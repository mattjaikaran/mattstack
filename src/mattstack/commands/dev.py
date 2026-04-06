"""Dev command: unified service start for fullstack monorepos."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer

from mattstack.utils.console import (
    console,
    create_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from mattstack.utils.docker import docker_compose_available, docker_running
from mattstack.utils.package_manager import (
    build_run_cmd,
    resolve_package_manager,
)
from mattstack.utils.process import check_port_available


def _has_backend(path: Path) -> bool:
    """Check if project has a Django backend."""
    backend_dir = path / "backend"
    return (backend_dir / "pyproject.toml").exists() and (backend_dir / "manage.py").exists()


def _has_frontend(path: Path) -> bool:
    """Check if project has a frontend."""
    frontend_dir = path / "frontend"
    pkg = frontend_dir / "package.json"
    if not pkg.exists():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        return "dev" in data.get("scripts", {})
    except (json.JSONDecodeError, OSError):
        return False


def _has_docker(path: Path) -> bool:
    """Check if project has docker-compose."""
    return (path / "docker-compose.yml").exists()


def _parse_services(services_str: str | None) -> set[str]:
    """Parse --services option into a set of service names."""
    if not services_str:
        return {"docker", "backend", "frontend"}
    return {s.strip().lower() for s in services_str.split(",") if s.strip()}


def run_dev(
    path: Path,
    services: str | None = None,
    no_docker: bool = False,
) -> None:
    """Start all development services (docker, backend, frontend)."""
    path = path.resolve()
    if not path.is_dir():
        print_error(f"Directory not found: {path}")
        raise typer.Exit(code=1)

    requested = _parse_services(services)
    if no_docker:
        requested.discard("docker")

    console.print()
    console.print("[bold cyan]mattstack dev[/bold cyan]")
    console.print()

    started: list[tuple[str, str, int | None]] = []  # (service, description, pid)
    backend_dir = path / "backend"
    frontend_dir = path / "frontend"

    # Docker infrastructure
    if "docker" in requested and _has_docker(path):
        if not docker_compose_available():
            print_error("docker compose not available")
            raise typer.Exit(code=1)
        if not docker_running():
            print_error("Docker daemon not running")
            raise typer.Exit(code=1)
        print_info("Starting Docker infrastructure...")
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print_error(f"Docker compose failed: {result.stderr or result.stdout}")
            raise typer.Exit(code=1)
        print_success("Docker infrastructure started")
        started.append(("docker", "docker compose up -d", None))
    elif "docker" in requested and not _has_docker(path):
        print_info("No docker-compose.yml found, skipping Docker")

    # Backend
    if "backend" in requested and _has_backend(path):
        if not check_port_available(8000):
            print_warning("Port 8000 already in use — backend may already be running")
        print_info("Starting backend dev server...")
        proc = subprocess.Popen(
            ["uv", "run", "python", "manage.py", "runserver"],
            cwd=backend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        started.append(("backend", "uv run python manage.py runserver (port 8000)", proc.pid))
        print_success(f"Backend started (PID {proc.pid})")
    elif "backend" in requested and not _has_backend(path):
        print_info("No backend found (backend/pyproject.toml + manage.py), skipping")

    # Frontend
    if "frontend" in requested and _has_frontend(path):
        if not check_port_available(3000):
            print_warning("Port 3000 already in use — frontend may already be running")
        print_info("Starting frontend dev server...")
        pm = resolve_package_manager(frontend_dir)
        cmd = build_run_cmd(pm, "dev")
        proc = subprocess.Popen(
            cmd.full,
            cwd=frontend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        port = 3000  # default for Vite/Next
        started.append(("frontend", f"{pm.value} run dev (port {port})", proc.pid))
        print_success(f"Frontend started (PID {proc.pid})")
    elif "frontend" in requested and not _has_frontend(path):
        print_info("No frontend with 'dev' script found, skipping")

    if not started:
        print_error("No services to start. Check --services and project structure.")
        raise typer.Exit(code=1)

    # Status table
    table = create_table("Services Started", ["Service", "Command", "PID"])
    for svc, desc, pid in started:
        pid_str = str(pid) if pid is not None else "N/A"
        table.add_row(svc, desc, pid_str)
    console.print(table)
    console.print()
    console.print(
        "[dim]Background processes running. Use Ctrl+C in their terminals to stop, "
        "or kill by PID.[/dim]"
    )
    console.print()
