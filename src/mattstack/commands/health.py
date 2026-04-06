"""Health command: service health checks for fullstack monorepos."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import typer

from mattstack.utils.console import (
    console,
    create_table,
    print_error,
    print_info,
)
from mattstack.utils.process import check_port_available


def _check_docker(path: Path) -> tuple[str, str]:
    """Check if Docker services are running."""
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "DOWN", result.stderr.strip() or "docker compose not available"
    output = result.stdout.strip()
    if not output:
        return "DOWN", "No containers running"
    # Count running containers
    lines = [line for line in output.splitlines() if line.strip()]
    return "UP", f"{len(lines)} container(s) running"


def _check_port_service(port: int, name: str) -> tuple[str, str]:
    """Check if a service is reachable on a port."""
    if check_port_available(port):
        # Port is free = service NOT running
        return "DOWN", f"Nothing listening on port {port}"
    return "UP", f"Listening on port {port}"


def _check_http(url: str) -> tuple[str, str]:
    """Check if an HTTP endpoint responds."""
    try:
        import urllib.request

        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return "UP", f"HTTP {resp.status}"
    except Exception as exc:
        return "DOWN", str(exc)


def run_health(
    path: Path,
    live: bool = False,
) -> None:
    """Run health checks on project services."""
    path = path.resolve()
    if not path.is_dir():
        print_error(f"Directory not found: {path}")
        raise typer.Exit(code=1)

    console.print()
    console.print("[bold cyan]mattstack health[/bold cyan]")
    console.print()

    start = time.perf_counter()
    checks: list[tuple[str, str, str, float]] = []  # (service, status, detail, ms)

    # 1. Docker
    print_info("Checking Docker...")
    t0 = time.perf_counter()
    status, detail = _check_docker(path)
    checks.append(("Docker", status, detail, (time.perf_counter() - t0) * 1000))

    # 2. PostgreSQL
    print_info("Checking PostgreSQL...")
    t0 = time.perf_counter()
    status, detail = _check_port_service(5432, "PostgreSQL")
    checks.append(("PostgreSQL", status, detail, (time.perf_counter() - t0) * 1000))

    # 3. Redis
    print_info("Checking Redis...")
    t0 = time.perf_counter()
    status, detail = _check_port_service(6379, "Redis")
    checks.append(("Redis", status, detail, (time.perf_counter() - t0) * 1000))

    # 4. Backend (live only)
    if live:
        print_info("Checking Backend (live)...")
        t0 = time.perf_counter()
        status, detail = _check_http("http://localhost:8000/api/docs")
        checks.append(("Backend", status, detail, (time.perf_counter() - t0) * 1000))
    else:
        print_info("Checking Backend port...")
        t0 = time.perf_counter()
        status, detail = _check_port_service(8000, "Backend")
        checks.append(("Backend", status, detail, (time.perf_counter() - t0) * 1000))

    # 5. Frontend (live only)
    if live:
        print_info("Checking Frontend (live)...")
        t0 = time.perf_counter()
        status, detail = _check_http("http://localhost:3000")
        checks.append(("Frontend", status, detail, (time.perf_counter() - t0) * 1000))
    else:
        print_info("Checking Frontend port...")
        t0 = time.perf_counter()
        status, detail = _check_port_service(3000, "Frontend")
        checks.append(("Frontend", status, detail, (time.perf_counter() - t0) * 1000))

    elapsed = time.perf_counter() - start

    # Results table
    table = create_table("Health Check", ["Service", "Status", "Details", "Time"])
    for service, status, detail, ms in checks:
        status_fmt = f"[green]{status}[/green]" if status == "UP" else f"[red]{status}[/red]"
        table.add_row(service, status_fmt, detail, f"{ms:.0f}ms")
    console.print()
    console.print(table)

    up_count = sum(1 for _, s, _, _ in checks if s == "UP")
    total = len(checks)
    console.print()
    console.print(f"[bold]{up_count}/{total} services healthy[/bold]")
    console.print(f"[dim]({elapsed:.1f}s)[/dim]")

    if up_count < total:
        raise typer.Exit(code=1)
