"""Workflow command: CI/CD workflow generation for fullstack monorepos."""

from __future__ import annotations

import time
from pathlib import Path

import typer

from mattstack.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)


def _detect_project_type(path: Path) -> str:
    """Detect if project is fullstack, backend-only, or frontend-only."""
    has_be = (path / "backend" / "pyproject.toml").exists()
    has_fe = (path / "frontend" / "package.json").exists()
    if has_be and has_fe:
        return "fullstack"
    if has_be:
        return "backend-only"
    if has_fe:
        return "frontend-only"
    return "unknown"


def _generate_github_actions(path: Path, project_type: str) -> str:
    """Generate GitHub Actions CI workflow YAML."""
    jobs: list[str] = []

    if project_type in ("fullstack", "backend-only"):
        jobs.append(_backend_lint_job())
        jobs.append(_backend_test_job())

    if project_type in ("fullstack", "frontend-only"):
        jobs.append(_frontend_lint_job())
        jobs.append(_frontend_test_job())
        jobs.append(_frontend_typecheck_job())

    jobs_block = "\n".join(jobs)

    return f"""name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
{jobs_block}
"""


def _backend_lint_job() -> str:
    return """  backend-lint:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check ."""


def _backend_test_job() -> str:
    return """  backend-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    defaults:
      run:
        working-directory: backend
    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: uv sync --frozen
      - run: uv run pytest -x -q"""


def _frontend_lint_job() -> str:
    return """  frontend-lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest
      - run: bun install --frozen-lockfile
      - run: bun run lint"""


def _frontend_test_job() -> str:
    return """  frontend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest
      - run: bun install --frozen-lockfile
      - run: bun run test"""


def _frontend_typecheck_job() -> str:
    return """  frontend-typecheck:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest
      - run: bun install --frozen-lockfile
      - run: bunx tsc --noEmit"""


def _generate_gitlab_ci(path: Path, project_type: str) -> str:
    """Generate GitLab CI configuration."""
    stages: list[str] = []
    jobs: list[str] = []

    if project_type in ("fullstack", "backend-only"):
        stages.extend(["lint", "test"])
        jobs.append("""
backend-lint:
  stage: lint
  image: python:3.13-slim
  before_script:
    - pip install uv
    - cd backend && uv sync --frozen
  script:
    - uv run ruff check .
    - uv run ruff format --check .""")

        jobs.append("""
backend-test:
  stage: test
  image: python:3.13-slim
  services:
    - postgres:17
    - redis:7
  variables:
    POSTGRES_DB: test_db
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    DATABASE_URL: postgresql://postgres:postgres@postgres:5432/test_db
    REDIS_URL: redis://redis:6379/0
  before_script:
    - pip install uv
    - cd backend && uv sync --frozen
  script:
    - uv run pytest -x -q""")

    if project_type in ("fullstack", "frontend-only"):
        if "lint" not in stages:
            stages.append("lint")
        if "test" not in stages:
            stages.append("test")

        jobs.append("""
frontend-lint:
  stage: lint
  image: oven/bun:latest
  before_script:
    - cd frontend && bun install --frozen-lockfile
  script:
    - bun run lint""")

        jobs.append("""
frontend-test:
  stage: test
  image: oven/bun:latest
  before_script:
    - cd frontend && bun install --frozen-lockfile
  script:
    - bun run test""")

        jobs.append("""
frontend-typecheck:
  stage: test
  image: oven/bun:latest
  before_script:
    - cd frontend && bun install --frozen-lockfile
  script:
    - bunx tsc --noEmit""")

    stages_str = "\n".join(f"  - {s}" for s in stages)
    jobs_str = "\n".join(jobs)

    return f"""stages:
{stages_str}
{jobs_str}
"""


def run_generate_workflow(
    path: Path,
    platform: str = "github-actions",
    dry_run: bool = False,
) -> None:
    """Generate CI/CD workflow configuration."""
    path = path.resolve()
    if not path.is_dir():
        print_error(f"Directory not found: {path}")
        raise typer.Exit(code=1)

    start = time.perf_counter()

    console.print()
    console.print("[bold cyan]mattstack workflow[/bold cyan]")
    console.print()

    project_type = _detect_project_type(path)
    if project_type == "unknown":
        print_error("Could not detect project type (no backend/ or frontend/ found)")
        raise typer.Exit(code=1)

    print_info(f"Detected project type: {project_type}")
    print_info(f"Platform: {platform}")

    if platform == "github-actions":
        content = _generate_github_actions(path, project_type)
        output_path = path / ".github" / "workflows" / "ci.yml"
    elif platform == "gitlab-ci":
        content = _generate_gitlab_ci(path, project_type)
        output_path = path / ".gitlab-ci.yml"
    else:
        print_error(f"Unknown platform: {platform}. Use: github-actions, gitlab-ci")
        raise typer.Exit(code=1)

    if dry_run:
        console.print()
        console.print(f"[bold]Would create:[/bold] {output_path}")
        console.print()
        console.print(content)
        elapsed = time.perf_counter() - start
        console.print(f"[dim]({elapsed:.1f}s)[/dim]")
        return

    # Write file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        print_warning(f"Overwriting existing {output_path.name}")
    output_path.write_text(content, encoding="utf-8")

    elapsed = time.perf_counter() - start
    print_success(f"Created {output_path}")
    console.print(f"[dim]({elapsed:.1f}s)[/dim]")
