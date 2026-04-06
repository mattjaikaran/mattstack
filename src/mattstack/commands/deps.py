"""Deps command: dependency management for fullstack monorepos."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Annotated

import typer

from mattstack.utils.console import (
    console,
    create_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)

deps_app = typer.Typer(
    name="deps",
    help="Dependency management (check outdated, update, audit).",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _has_backend(path: Path) -> bool:
    return (path / "backend" / "pyproject.toml").exists()


def _has_frontend(path: Path) -> bool:
    return (path / "frontend" / "package.json").exists()


def _check_backend(path: Path) -> list[tuple[str, str, str]]:
    """Return list of (package, current, latest) for outdated backend deps."""
    backend_dir = path / "backend"
    result = subprocess.run(
        ["uv", "run", "pip", "list", "--outdated", "--format", "json"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print_warning(f"Backend outdated check failed: {result.stderr.strip()}")
        return []
    try:
        packages = json.loads(result.stdout)
    except json.JSONDecodeError:
        print_warning("Failed to parse backend outdated output")
        return []
    return [
        (p["name"], p.get("version", "?"), p.get("latest_version", "?"))
        for p in packages
    ]


def _check_frontend(path: Path) -> list[tuple[str, str, str]]:
    """Return list of (package, current, latest) for outdated frontend deps."""
    frontend_dir = path / "frontend"
    result = subprocess.run(
        ["bun", "outdated"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and not result.stdout.strip():
        print_warning(f"Frontend outdated check failed: {result.stderr.strip()}")
        return []
    # Parse bun outdated text output: lines like "package  current  update  latest"
    outdated: list[tuple[str, str, str]] = []
    lines = result.stdout.strip().splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and not parts[0].startswith(("Package", "---", "│", "┌", "└", "├")):
            outdated.append((parts[0], parts[1], parts[-1]))
    return outdated


@deps_app.command("check")
def check(
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project path"),
    ] = None,
) -> None:
    """Show outdated packages for backend and frontend."""
    project = (path or Path.cwd()).resolve()
    start = time.perf_counter()

    has_be = _has_backend(project)
    has_fe = _has_frontend(project)

    if not has_be and not has_fe:
        print_error("No backend or frontend found.")
        raise typer.Exit(code=1)

    console.print()
    console.print("[bold cyan]mattstack deps check[/bold cyan]")
    console.print()

    total_outdated = 0

    if has_be:
        print_info("Checking backend dependencies...")
        be_outdated = _check_backend(project)
        if be_outdated:
            table = create_table("Backend — Outdated Packages", ["Package", "Current", "Latest"])
            for name, current, latest in be_outdated:
                table.add_row(name, current, f"[yellow]{latest}[/yellow]")
            console.print(table)
            total_outdated += len(be_outdated)
        else:
            print_success("Backend dependencies are up to date")
    else:
        print_info("No backend found, skipping")

    if has_fe:
        print_info("Checking frontend dependencies...")
        fe_outdated = _check_frontend(project)
        if fe_outdated:
            table = create_table("Frontend — Outdated Packages", ["Package", "Current", "Latest"])
            for name, current, latest in fe_outdated:
                table.add_row(name, current, f"[yellow]{latest}[/yellow]")
            console.print(table)
            total_outdated += len(fe_outdated)
        else:
            print_success("Frontend dependencies are up to date")
    else:
        print_info("No frontend found, skipping")

    elapsed = time.perf_counter() - start
    console.print()
    if total_outdated:
        print_warning(f"{total_outdated} outdated package(s) found")
    console.print(f"[dim]({elapsed:.1f}s)[/dim]")


@deps_app.command("update")
def update(
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project path"),
    ] = None,
    backend_only: Annotated[
        bool,
        typer.Option("--backend-only", help="Update backend only"),
    ] = False,
    frontend_only: Annotated[
        bool,
        typer.Option("--frontend-only", help="Update frontend only"),
    ] = False,
    major: Annotated[
        bool,
        typer.Option("--major", help="Include major version updates"),
    ] = False,
) -> None:
    """Update dependencies for backend and/or frontend."""
    project = (path or Path.cwd()).resolve()
    start = time.perf_counter()

    has_be = _has_backend(project)
    has_fe = _has_frontend(project)

    run_be = (backend_only or (not frontend_only and has_be)) and has_be
    run_fe = (frontend_only or (not backend_only and has_fe)) and has_fe

    if not run_be and not run_fe:
        print_error("No backend or frontend found to update.")
        raise typer.Exit(code=1)

    console.print()
    console.print("[bold cyan]mattstack deps update[/bold cyan]")
    console.print()

    results: list[tuple[str, bool]] = []

    if run_be:
        backend_dir = project / "backend"
        print_info("Updating backend dependencies...")

        lock_args = ["uv", "lock", "--upgrade"]
        lock_result = subprocess.run(lock_args, cwd=backend_dir, capture_output=True, text=True)
        if lock_result.returncode != 0:
            print_error(f"uv lock failed: {lock_result.stderr.strip()}")
            results.append(("backend", False))
        else:
            sync_result = subprocess.run(
                ["uv", "sync"], cwd=backend_dir, capture_output=True, text=True,
            )
            ok = sync_result.returncode == 0
            if ok:
                print_success("Backend dependencies updated")
            else:
                print_error(f"uv sync failed: {sync_result.stderr.strip()}")
            results.append(("backend", ok))

    if run_fe:
        frontend_dir = project / "frontend"
        print_info("Updating frontend dependencies...")

        update_args = ["bun", "update"]
        if major:
            update_args.append("--latest")
        fe_result = subprocess.run(
            update_args, cwd=frontend_dir, capture_output=True, text=True,
        )
        ok = fe_result.returncode == 0
        if ok:
            print_success("Frontend dependencies updated")
        else:
            print_error(f"bun update failed: {fe_result.stderr.strip()}")
        results.append(("frontend", ok))

    elapsed = time.perf_counter() - start

    table = create_table("Update Results", ["Component", "Status"])
    all_ok = True
    for name, ok in results:
        all_ok &= ok
        status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        table.add_row(name, status)
    console.print()
    console.print(table)
    console.print(f"[dim]({elapsed:.1f}s)[/dim]")

    if not all_ok:
        raise typer.Exit(code=1)


@deps_app.command("audit")
def audit(
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project path"),
    ] = None,
) -> None:
    """Run security audit on dependencies."""
    project = (path or Path.cwd()).resolve()
    start = time.perf_counter()

    has_be = _has_backend(project)
    has_fe = _has_frontend(project)

    if not has_be and not has_fe:
        print_error("No backend or frontend found.")
        raise typer.Exit(code=1)

    console.print()
    console.print("[bold cyan]mattstack deps audit[/bold cyan]")
    console.print()

    findings: list[tuple[str, str, str, str]] = []  # (source, package, severity, detail)

    if has_be:
        backend_dir = project / "backend"
        print_info("Auditing backend dependencies...")
        result = subprocess.run(
            ["uv", "run", "pip-audit", "--format", "json"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 127 or "No module named" in result.stderr:
            print_warning("pip-audit not available — install with: uv add --dev pip-audit")
        elif result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                vulns = data.get("dependencies", [])
                for dep in vulns:
                    for vuln in dep.get("vulns", []):
                        findings.append((
                            "backend",
                            dep["name"],
                            vuln.get("fix_versions", ["?"])[0] if vuln.get("fix_versions") else "?",
                            vuln.get("id", "unknown"),
                        ))
            except json.JSONDecodeError:
                # pip-audit may output non-json on some versions
                if result.returncode != 0:
                    print_warning(f"pip-audit returned errors:\n{result.stderr.strip()}")
                else:
                    print_success("Backend audit passed — no vulnerabilities found")
        else:
            print_success("Backend audit passed — no vulnerabilities found")

    if has_fe:
        frontend_dir = project / "frontend"
        print_info("Auditing frontend dependencies...")
        result = subprocess.run(
            ["bun", "audit"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 and "error" in result.stderr.lower():
            # Fallback: bun audit may not be supported in all versions
            print_warning("bun audit not supported in this version, trying npm audit...")
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    for name, advisory in data.get("vulnerabilities", {}).items():
                        findings.append((
                            "frontend",
                            name,
                            advisory.get("severity", "unknown"),
                            advisory.get("via", [{}])[0].get("title", "") if isinstance(advisory.get("via", [{}])[0], dict) else str(advisory.get("via", [""])[0]),
                        ))
                except json.JSONDecodeError:
                    pass
        elif result.stdout.strip():
            console.print(result.stdout)

    elapsed = time.perf_counter() - start

    if findings:
        table = create_table(
            "Security Findings", ["Source", "Package", "Severity/Fix", "ID/Detail"],
        )
        for source, pkg, severity, detail in findings:
            table.add_row(source, pkg, f"[red]{severity}[/red]", detail)
        console.print(table)
        print_warning(f"{len(findings)} vulnerability(ies) found")
    else:
        print_success("No vulnerabilities found")

    console.print(f"[dim]({elapsed:.1f}s)[/dim]")
