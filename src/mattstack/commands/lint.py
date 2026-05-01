"""Lint command: unified linter for fullstack monorepos."""

from __future__ import annotations

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import typer

from mattstack.utils.console import console, create_table, print_error, print_info, print_success
from mattstack.utils.package_manager import (
    build_run_cmd,
    resolve_package_manager,
)


def _has_backend(path: Path) -> bool:
    """Check if project has a Python backend."""
    backend_dir = path / "backend"
    return (backend_dir / "pyproject.toml").exists()


def _has_frontend(path: Path) -> bool:
    """Check if project has a frontend with lint script."""
    frontend_dir = path / "frontend"
    pkg = frontend_dir / "package.json"
    if not pkg.exists():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        scripts = data.get("scripts", {})
        return "lint" in scripts or ("lint:fix" in scripts)
    except (json.JSONDecodeError, OSError):
        return False


def _run_backend_lint(
    path: Path,
    fix: bool,
    format_check: bool,
) -> subprocess.CompletedProcess[str]:
    """Run ruff check (and optionally format check) on backend."""
    backend_dir = path / "backend"
    results: list[subprocess.CompletedProcess[str]] = []

    check_args = ["uv", "run", "ruff", "check", "."]
    if fix:
        check_args.append("--fix")
    result = subprocess.run(check_args, cwd=backend_dir, text=True, capture_output=True)
    results.append(result)

    if format_check:
        fmt_args = ["uv", "run", "ruff", "format"]
        if not fix:
            fmt_args.append("--check")
        fmt_args.append(".")
        fmt_result = subprocess.run(fmt_args, cwd=backend_dir, text=True, capture_output=True)
        results.append(fmt_result)

    combined_stdout = "\n".join(r.stdout for r in results if r.stdout)
    combined_stderr = "\n".join(r.stderr for r in results if r.stderr)
    combined_code = 0 if all(r.returncode == 0 for r in results) else 1
    return subprocess.CompletedProcess(
        args=[],
        returncode=combined_code,
        stdout=combined_stdout,
        stderr=combined_stderr,
    )


def _run_frontend_lint(path: Path, fix: bool) -> subprocess.CompletedProcess[str]:
    """Run frontend lint via package manager."""
    frontend_dir = path / "frontend"
    pm = resolve_package_manager(frontend_dir)
    pkg = json.loads((frontend_dir / "package.json").read_text(encoding="utf-8"))
    scripts = pkg.get("scripts", {})

    script = "lint:fix" if (fix and "lint:fix" in scripts) else "lint"
    if script not in scripts:
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr=f"No '{script}' script in package.json",
        )
    cmd = build_run_cmd(pm, script)
    return subprocess.run(cmd.full, cwd=frontend_dir, text=True, capture_output=True)


def _stream_process(proc: subprocess.Popen[str], label: str, lock: threading.Lock) -> int:
    """Stream stdout lines from proc to console, prefixing each with label."""
    assert proc.stdout is not None
    for line in proc.stdout:
        with lock:
            console.print(f"[dim]{label}[/dim] {line}", end="")
    proc.wait()
    return proc.returncode if proc.returncode is not None else 1


def run_lint(
    path: Path,
    fix: bool = False,
    format_check: bool = False,
    backend_only: bool = False,
    frontend_only: bool = False,
    parallel: bool = False,
) -> None:
    """Run linters across backend and frontend."""
    path = path.resolve()
    if not path.is_dir():
        print_error(f"Directory not found: {path}")
        raise typer.Exit(code=1)

    has_be = _has_backend(path)
    has_fe = _has_frontend(path)

    run_backend = (backend_only or (not frontend_only and has_be)) and has_be
    run_frontend = (frontend_only or (not backend_only and has_fe)) and has_fe

    if not run_backend and not run_frontend:
        print_error("No backend or frontend to lint.")
        raise typer.Exit(code=1)

    console.print()
    console.print("[bold cyan]mattstack lint[/bold cyan]")
    console.print()

    start = time.perf_counter()
    results: list[tuple[str, int, str]] = []

    if parallel and run_backend and run_frontend:
        print_info("Linting backend and frontend in parallel...")
        be_args = ["uv", "run", "ruff", "check", "."]
        if fix:
            be_args.append("--fix")
        be_proc = subprocess.Popen(
            be_args,
            cwd=path / "backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        frontend_dir = path / "frontend"
        pm = resolve_package_manager(frontend_dir)
        pkg = json.loads((frontend_dir / "package.json").read_text(encoding="utf-8"))
        scripts = pkg.get("scripts", {})
        script = "lint:fix" if (fix and "lint:fix" in scripts) else "lint"
        fe_cmd = build_run_cmd(pm, script)
        fe_proc = subprocess.Popen(
            fe_cmd.full,
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        lock = threading.Lock()
        with ThreadPoolExecutor(max_workers=2) as executor:
            be_future = executor.submit(_stream_process, be_proc, "[backend]", lock)
            fe_future = executor.submit(_stream_process, fe_proc, "[frontend]", lock)
        be_code = be_future.result()
        fe_code = fe_future.result()
        results = [("backend", be_code, ""), ("frontend", fe_code, "")]
    else:
        if run_backend:
            print_info("Linting backend...")
            be_result = _run_backend_lint(path, fix, format_check)
            if be_result.stdout:
                console.print(be_result.stdout)
            if be_result.stderr:
                console.print(be_result.stderr)
            results.append(("backend", be_result.returncode, be_result.stdout + be_result.stderr))

        if run_frontend:
            print_info("Linting frontend...")
            fe_result = _run_frontend_lint(path, fix)
            if fe_result.stdout:
                console.print(fe_result.stdout)
            if fe_result.stderr:
                console.print(fe_result.stderr)
            results.append(("frontend", fe_result.returncode, fe_result.stdout + fe_result.stderr))

    elapsed = time.perf_counter() - start

    table = create_table("Lint Results", ["Component", "Status"])
    all_ok = True
    for name, code, _ in results:
        ok = code == 0
        all_ok &= ok
        status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        table.add_row(name, status)
    console.print()
    console.print(table)
    console.print(f"[dim]({elapsed:.1f}s)[/dim]")

    if not all_ok:
        if not fix:
            console.print("[dim]Tip: run `mattstack lint --fix` to auto-fix issues[/dim]")
        raise typer.Exit(code=1)
    print_success("All lint checks passed")
