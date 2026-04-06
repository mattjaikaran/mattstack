"""Test command: unified test runner for fullstack monorepos."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import typer

from mattstack.utils.console import console, create_table, print_error, print_info, print_success
from mattstack.utils.package_manager import (
    build_run_cmd,
    resolve_package_manager,
)


def _has_backend(path: Path) -> bool:
    """Check if project has a Python backend with pytest."""
    backend_dir = path / "backend"
    return (backend_dir / "pyproject.toml").exists()


def _has_frontend(path: Path) -> bool:
    """Check if project has a frontend with test script."""
    frontend_dir = path / "frontend"
    pkg = frontend_dir / "package.json"
    if not pkg.exists():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        scripts = data.get("scripts", {})
        return "test" in scripts or "test:coverage" in scripts
    except (json.JSONDecodeError, OSError):
        return False


def _run_backend_tests(path: Path, coverage: bool) -> subprocess.CompletedProcess[str]:
    """Run backend tests with pytest."""
    backend_dir = path / "backend"
    args = ["uv", "run", "pytest", "-v"]
    if coverage:
        args.extend(["--cov", "--cov-report=term-missing"])
    return subprocess.run(args, cwd=backend_dir, text=True)


def _run_frontend_tests(path: Path, coverage: bool) -> subprocess.CompletedProcess[str]:
    """Run frontend tests via package manager."""
    frontend_dir = path / "frontend"
    pm = resolve_package_manager(frontend_dir)
    pkg = json.loads((frontend_dir / "package.json").read_text(encoding="utf-8"))
    scripts = pkg.get("scripts", {})

    if coverage and "test:coverage" in scripts:
        cmd = build_run_cmd(pm, "test:coverage")
    elif "test" in scripts:
        cmd = build_run_cmd(pm, "test")
    else:
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="No 'test' or 'test:coverage' script in package.json",
        )
    return subprocess.run(cmd.full, cwd=frontend_dir, text=True)


def run_test(
    path: Path,
    backend_only: bool = False,
    frontend_only: bool = False,
    coverage: bool = False,
    parallel: bool = False,
) -> None:
    """Run tests across backend and frontend."""
    path = path.resolve()
    if not path.is_dir():
        print_error(f"Directory not found: {path}")
        raise typer.Exit(code=1)

    has_be = _has_backend(path)
    has_fe = _has_frontend(path)

    run_backend = (backend_only or (not frontend_only and has_be)) and has_be
    run_frontend = (frontend_only or (not backend_only and has_fe)) and has_fe

    if not run_backend and not run_frontend:
        print_error("No backend or frontend tests found.")
        raise typer.Exit(code=1)

    console.print()
    console.print("[bold cyan]mattstack test[/bold cyan]")
    console.print()

    start = time.perf_counter()
    results: list[tuple[str, int]] = []

    if parallel and run_backend and run_frontend:
        print_info("Running backend and frontend tests in parallel...")
        be_args = ["uv", "run", "pytest", "-v"]
        if coverage:
            be_args.extend(["--cov", "--cov-report=term-missing"])
        be_proc = subprocess.Popen(
            be_args,
            cwd=path / "backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        fe_pkg = json.loads((path / "frontend" / "package.json").read_text(encoding="utf-8"))
        fe_scripts = fe_pkg.get("scripts", {})
        pm = resolve_package_manager(path / "frontend")
        script = "test:coverage" if (coverage and "test:coverage" in fe_scripts) else "test"
        fe_cmd = build_run_cmd(pm, script)
        fe_proc = subprocess.Popen(
            fe_cmd.full,
            cwd=path / "frontend",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        be_out, _ = be_proc.communicate()
        fe_out, _ = fe_proc.communicate()
        be_code = be_proc.returncode or 0
        fe_code = fe_proc.returncode or 0
        console.print("[bold]Backend:[/bold]")
        console.print(be_out)
        console.print("[bold]Frontend:[/bold]")
        console.print(fe_out)
        results = [("backend", be_code), ("frontend", fe_code)]
    else:
        if run_backend:
            print_info("Running backend tests...")
            be_result = _run_backend_tests(path, coverage)
            if be_result.stdout:
                console.print(be_result.stdout)
            if be_result.stderr and be_result.stdout != be_result.stderr:
                console.print(be_result.stderr)
            results.append(("backend", be_result.returncode))

        if run_frontend:
            print_info("Running frontend tests...")
            fe_result = _run_frontend_tests(path, coverage)
            if fe_result.stdout:
                console.print(fe_result.stdout)
            if fe_result.stderr:
                console.print(fe_result.stderr)
            results.append(("frontend", fe_result.returncode))

    # Summary table
    table = create_table("Test Results", ["Component", "Status"])
    all_ok = True
    for name, code in results:
        ok = code == 0
        all_ok &= ok
        status = "[green]PASS[/green]" if ok else "[red]FAIL[/red]"
        table.add_row(name, status)
    elapsed = time.perf_counter() - start
    console.print()
    console.print(table)
    console.print(f"[dim]({elapsed:.1f}s)[/dim]")

    if not all_ok:
        raise typer.Exit(code=1)
    print_success("All tests passed")
