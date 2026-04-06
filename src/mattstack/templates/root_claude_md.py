"""Root CLAUDE.md template for generated projects."""

from __future__ import annotations

from mattstack.config import FrontendFramework, ProjectConfig

_RSBUILD = FrontendFramework.REACT_RSBUILD


def generate_claude_md(config: ProjectConfig) -> str:
    """Generate CLAUDE.md for AI assistant context."""
    sections = [
        _header(config),
        _structure(config),
        _tech(config),
        _rules(config),
        _commands(config),
        _ports(config),
        _env_vars(config),
    ]

    if config.has_backend:
        sections.append(_backend(config))

    if config.has_frontend:
        sections.append(_frontend(config))

    if config.include_ios:
        sections.append(_ios(config))

    if config.has_backend:
        sections.append(_docker_services(config))

    sections.append(_mattstack_integration(config))

    return "\n\n".join(sections) + "\n"


def _header(config: ProjectConfig) -> str:
    variant = " (B2B)" if config.is_b2b else ""
    return f"# {config.display_name}{variant}"


def _structure(config: ProjectConfig) -> str:
    parts: list[str] = []
    if config.has_backend:
        parts.append("- `backend/` — Django API (django-ninja, Python 3.12+)")
    if config.has_frontend:
        if config.is_nextjs:
            parts.append("- `frontend/` — Next.js (App Router, TypeScript, Tailwind)")
        elif config.frontend_framework == _RSBUILD:
            parts.append("- `frontend/` — React + Rsbuild + TypeScript (TanStack Router)")
        else:
            fw = config.frontend_framework
            router = "TanStack Router" if fw == FrontendFramework.REACT_VITE else "React Router"
            parts.append(f"- `frontend/` — React + Vite + TypeScript ({router})")
    if config.has_backend:
        services = ["PostgreSQL 17"]
        if config.use_redis:
            services.append("Redis 7")
        parts.append(f"- `docker-compose.yml` — {', '.join(services)}")
    if config.include_ios:
        parts.append("- `ios/` — SwiftUI iOS client (iOS 17+)")
    return "## Structure\n\n" + "\n".join(parts)


def _tech(config: ProjectConfig) -> str:
    parts: list[str] = []
    if config.has_backend:
        parts.append("- Backend: Python 3.12+, Django, django-ninja, PostgreSQL 17")
        if config.use_celery:
            parts.append("- Background: Celery + Redis")
    if config.has_frontend:
        if config.is_nextjs:
            parts.append("- Frontend: Next.js (App Router), TypeScript (strict)")
        elif config.frontend_framework == _RSBUILD:
            parts.append("- Frontend: React 19, Rsbuild (Rspack), TypeScript (strict)")
        else:
            parts.append("- Frontend: React 18, Vite, TypeScript (strict)")
    if config.include_ios:
        parts.append("- iOS: SwiftUI, MVVM, async/await, iOS 17+")
    return "## Tech Stack\n\n" + "\n".join(parts)


def _rules(config: ProjectConfig) -> str:
    lines: list[str] = [
        "## Rules",
        "",
        "**CRITICAL — AI agents MUST follow these rules:**",
        "",
        "- **Python packages**: ALWAYS use `uv`. NEVER use pip, poetry, or conda.",
        "- **JavaScript packages**: ALWAYS use `bun`. NEVER use `npm`, `yarn`, or `pnpm`.",
    ]

    if config.has_backend:
        docker_rule = (
            "- **Docker**: Run `docker compose up -d` before dev servers. "
            "NEVER install PostgreSQL or Redis locally."
        )
        lines.append(docker_rule)
        lines.append(
            "- **API framework**: Backend uses django-ninja (Pydantic models, type-safe). "
            "NEVER use Django REST Framework serializers."
        )
        lines.append(
            "- **Migrations**: ALWAYS run `cd backend && uv run python manage.py makemigrations "
            "&& uv run python manage.py migrate` after model changes."
        )

    lines.append("- **Type safety**: ALWAYS use type hints (Python). ALWAYS use strict TypeScript.")

    if config.is_fullstack:
        lines.append("- **Testing**: `uv run pytest -v` in backend, `bun run test` in frontend.")
        lines.append("- **Linting**: `uv run ruff check .` in backend, `bun run lint` in frontend.")
        fmt = "`uv run ruff format .` in backend, `bun run format` in frontend."
        lines.append(f"- **Formatting**: {fmt}")
    elif config.has_backend:
        lines.append("- **Testing**: Run `uv run pytest -v` in `backend/`.")
        lines.append("- **Linting**: Run `uv run ruff check .` in `backend/`.")
        lines.append("- **Formatting**: Run `uv run ruff format .` in `backend/`.")
    else:
        lines.append("- **Testing**: Run `bun run test` in `frontend/`.")
        lines.append("- **Linting**: Run `bun run lint` in `frontend/`.")
        lines.append("- **Formatting**: Run `bun run format` in `frontend/`.")

    env_desc = _env_files_description(config)
    if env_desc:
        lines.append(f"- **Env files**: {env_desc}")

    lines.append(
        "- **mattstack**: `mattstack dev` (start all), `mattstack test`, "
        "`mattstack lint`, `mattstack audit`."
    )

    return "\n".join(lines)


def _env_files_description(config: ProjectConfig) -> str:
    if config.has_backend and config.has_frontend:
        return "Root `.env` for Docker services. `frontend/.env.local` for frontend-specific vars."
    if config.has_backend:
        return "Root `.env` for Django and Docker services."
    if config.has_frontend:
        return "`frontend/.env.local` for frontend-specific vars."
    return ""


def _commands(config: ProjectConfig) -> str:
    lines = [
        "## Commands",
        "",
        "```bash",
        "make setup              # Install all dependencies",
    ]
    if config.has_backend:
        lines.append("make up                 # Start Docker services (PostgreSQL, Redis)")
        lines.append("make down               # Stop Docker services")
    if config.has_backend:
        lines.append("make backend-dev        # Django dev server (port 8000)")
    if config.has_frontend:
        if config.is_nextjs:
            label = "Next.js"
        elif config.frontend_framework == _RSBUILD:
            label = "Rsbuild"
        else:
            label = "Vite"
        lines.append(f"make frontend-dev       # {label} dev server (port 3000)")
    if config.is_fullstack:
        dev_desc = "Start all dev servers (docker + backend + frontend)"
    elif config.has_backend:
        dev_desc = "Start dev servers (docker + backend)"
    else:
        dev_desc = "Start frontend dev server"
    test_desc = "Run all tests (backend + frontend)" if config.is_fullstack else "Run tests"
    lines.append(f"mattstack dev          # {dev_desc}")
    lines.append(f"mattstack test         # {test_desc}")
    lines.append("mattstack lint         # Lint all code")
    lines.append("mattstack lint --fix   # Auto-fix lint issues")
    lines.append("mattstack env check    # Verify .env files are in sync")
    lines.append("mattstack audit        # Run static analysis")
    lines.append("```")
    return "\n".join(lines)


def _ports(config: ProjectConfig) -> str:
    rows: list[tuple[str, str, str]] = []
    if config.has_backend:
        rows.append(("Django API", "8000", "http://localhost:8000"))
        rows.append(("PostgreSQL", "5432", "—"))
        if config.use_redis:
            rows.append(("Redis", "6379", "—"))
        rows.append(("API Docs", "8000", "http://localhost:8000/api/docs"))
    if config.has_frontend:
        rows.append(("Frontend", "3000", "http://localhost:3000"))
    if not rows:
        return ""
    table = "| Service | Port | URL |\n|---------|------|-----|\n"
    table += "\n".join(f"| {svc} | {port} | {url} |" for svc, port, url in rows)
    return "## Ports\n\n" + table


def _env_vars(config: ProjectConfig) -> str:
    parts: list[str] = ["## Environment Variables", ""]
    if config.has_backend:
        parts.append("- Root `.env`: `DATABASE_URL`, `DJANGO_SECRET_KEY`, `REDIS_URL` (if Redis)")
    if config.has_frontend:
        if config.is_nextjs:
            api_var = "NEXT_PUBLIC_API_BASE_URL"
        elif config.frontend_framework == _RSBUILD:
            api_var = "PUBLIC_API_BASE_URL"
        else:
            api_var = "VITE_API_BASE_URL"
        parts.append(f"- Frontend: `{api_var}` for API base URL")
    if not config.has_backend and not config.has_frontend:
        return ""
    return "\n".join(parts)


def _backend(config: ProjectConfig) -> str:
    lines = [
        "## Backend",
        "",
        "- Language: Python 3.12+",
        "- Framework: Django + django-ninja",
        "- Package manager: uv (NEVER pip)",
        "- Testing: pytest",
        "- Linting: ruff",
        "- Database: PostgreSQL 17 (via Docker)",
        "- API docs: http://localhost:8000/api/docs (Swagger UI)",
    ]
    if config.use_celery:
        lines.append("- Background jobs: Celery (run with `docker compose --profile celery up`)")
    if config.is_b2b:
        lines.append("- B2B: Organizations, teams, RBAC (role-based access control)")
    return "\n".join(lines)


def _frontend(config: ProjectConfig) -> str:
    if config.is_nextjs:
        return """## Frontend

- Language: TypeScript (strict mode)
- Framework: Next.js (App Router)
- Routing: App Router (file-based)
- Package manager: bun (NEVER npm/yarn)
- Styling: Tailwind CSS
- API base: `NEXT_PUBLIC_API_BASE_URL` env var
- API routes: `app/api/` directory
- Dev server: `cd frontend && bun run dev` (Next.js dev server on port 3000)"""
    if config.frontend_framework == _RSBUILD:
        return """## Frontend

- Language: TypeScript (strict mode)
- Framework: React 19 + Rsbuild (Rspack, Rust-powered)
- Routing: TanStack Router (file-based)
- Package manager: bun (NEVER npm/yarn)
- Styling: Tailwind CSS
- API base: `PUBLIC_API_BASE_URL` env var
- State management: TanStack Query (server), Zustand (client)
- Build config: `rsbuild.config.ts` (NOT vite.config.ts)"""
    return """## Frontend

- Language: TypeScript (strict mode)
- Framework: React 18 + Vite
- Routing: TanStack Router
- Package manager: bun (NEVER npm/yarn)
- Styling: Tailwind CSS
- API base: `VITE_API_BASE_URL` env var
- State management: TanStack Query (server state)"""


def _ios(config: ProjectConfig) -> str:
    return """## iOS

- SwiftUI with MVVM pattern
- Async/await networking
- iOS 17+ minimum deployment target"""


def _docker_services(config: ProjectConfig) -> str:
    parts = ["## Docker Services", "", "- `db`: PostgreSQL 17"]
    if config.use_redis:
        parts.append("- `redis`: Redis 7")
    parts.append("- `api-dev`: Django dev server (when using Docker)")
    if config.use_celery:
        parts.append("- `celery-worker`, `celery-beat`: Celery (profile: celery)")
    return "\n".join(parts)


def _mattstack_integration(config: ProjectConfig) -> str:
    return """## mattstack Integration

This project was scaffolded with `mattstack`. The CLI provides unified commands:
- `mattstack dev` — Start all services (Docker + backend + frontend)
- `mattstack test` — Run all tests
- `mattstack lint` — Lint all code
- `mattstack env check` — Compare .env files
- `mattstack audit` — Static analysis (quality, types, endpoints, tests, dependencies)"""
