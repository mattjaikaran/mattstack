"""Database management commands for mattstack projects."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Annotated

import typer

from mattstack.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)

db_app = typer.Typer(
    name="db",
    help="Database management commands (Django).",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _resolve_backend(path: Path) -> Path:
    """Resolve and validate the backend directory."""
    backend = path.resolve() / "backend"
    if not backend.is_dir():
        print_error(f"Backend directory not found: {backend}")
        raise typer.Exit(code=1)
    if not (backend / "manage.py").exists():
        print_error(f"No manage.py found in {backend}")
        raise typer.Exit(code=1)
    return backend


def _run_manage(
    backend: Path,
    args: list[str],
    *,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a Django management command via uv."""
    cmd = ["uv", "run", "python", "manage.py", *args]
    print_info(f"Running: {' '.join(cmd)}")
    start = time.monotonic()
    result = subprocess.run(
        cmd,
        cwd=backend,
        text=True,
        capture_output=capture,
    )
    elapsed = time.monotonic() - start
    console.print(f"[dim]Completed in {elapsed:.1f}s (exit code {result.returncode})[/dim]")
    return result


@db_app.command()
def migrate(
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
) -> None:
    """Run Django migrations."""
    backend = _resolve_backend(path or Path.cwd())
    result = _run_manage(backend, ["migrate"])
    if result.returncode == 0:
        print_success("Migrations applied")
    else:
        print_error("Migration failed")
        raise typer.Exit(code=result.returncode)


@db_app.command()
def makemigrations(
    app_label: Annotated[
        str | None,
        typer.Option("--app", "-a", help="Target specific Django app"),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
) -> None:
    """Create new Django migrations."""
    backend = _resolve_backend(path or Path.cwd())
    args = ["makemigrations"]
    if app_label:
        args.append(app_label)
    result = _run_manage(backend, args)
    if result.returncode == 0:
        print_success("Migrations created")
    else:
        print_error("makemigrations failed")
        raise typer.Exit(code=result.returncode)


@db_app.command()
def status(
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
) -> None:
    """Show migration status."""
    backend = _resolve_backend(path or Path.cwd())
    result = _run_manage(backend, ["showmigrations"])
    if result.returncode != 0:
        print_error("Failed to show migrations")
        raise typer.Exit(code=result.returncode)


@db_app.command()
def seed(
    fresh: Annotated[
        bool,
        typer.Option("--fresh", help="Reset database before seeding"),
    ] = False,
    file: Annotated[
        str | None,
        typer.Option("--file", "-f", help="Path to seed file (relative to backend/)"),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
) -> None:
    """Seed database with sample data."""
    backend = _resolve_backend(path or Path.cwd())

    if fresh:
        print_warning("Flushing all data before seeding...")
        flush_result = _run_manage(backend, ["flush", "--no-input"])
        if flush_result.returncode != 0:
            print_error("Database flush failed")
            raise typer.Exit(code=flush_result.returncode)
        migrate_result = _run_manage(backend, ["migrate"])
        if migrate_result.returncode != 0:
            print_error("Migration after flush failed")
            raise typer.Exit(code=migrate_result.returncode)

    seed_file = _resolve_seed_file(backend, file)
    if seed_file is None:
        print_warning("No seed file found")
        print_info("Expected: backend/seed.py or backend/seeds/ directory")
        print_info("Create a seed file and re-run this command")
        raise typer.Exit(code=1)

    print_info(f"Running seed file: {seed_file.relative_to(backend)}")
    start = time.monotonic()
    result = subprocess.run(
        ["uv", "run", "python", str(seed_file.relative_to(backend))],
        cwd=backend,
        text=True,
    )
    elapsed = time.monotonic() - start
    console.print(f"[dim]Completed in {elapsed:.1f}s (exit code {result.returncode})[/dim]")

    if result.returncode == 0:
        print_success("Database seeded")
    else:
        print_error("Seed failed")
        raise typer.Exit(code=result.returncode)


def _resolve_seed_file(backend: Path, file_override: str | None) -> Path | None:
    """Find the seed file to execute."""
    if file_override:
        candidate = backend / file_override
        return candidate if candidate.exists() else None

    # Check seed.py
    seed_py = backend / "seed.py"
    if seed_py.exists():
        return seed_py

    # Check seeds/ directory for __main__.py or run.py
    seeds_dir = backend / "seeds"
    if seeds_dir.is_dir():
        for name in ["__main__.py", "run.py", "seed.py"]:
            candidate = seeds_dir / name
            if candidate.exists():
                return candidate

    return None


@db_app.command()
def reset(
    seed_after: Annotated[
        bool,
        typer.Option("--seed", help="Seed database after reset"),
    ] = False,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
) -> None:
    """Reset database (dev only). Flushes all data and re-migrates."""
    import questionary

    backend = _resolve_backend(path or Path.cwd())

    confirmed = questionary.confirm(
        "This will delete all data. Are you sure?",
        default=False,
    ).ask()

    if not confirmed:
        print_info("Aborted")
        raise typer.Exit(code=0)

    print_warning("Flushing database...")
    flush_result = _run_manage(backend, ["flush", "--no-input"])
    if flush_result.returncode != 0:
        print_error("Database flush failed")
        raise typer.Exit(code=flush_result.returncode)

    print_info("Running migrations...")
    migrate_result = _run_manage(backend, ["migrate"])
    if migrate_result.returncode != 0:
        print_error("Migration after reset failed")
        raise typer.Exit(code=migrate_result.returncode)

    print_success("Database reset complete")

    if seed_after:
        seed_file = _resolve_seed_file(backend, None)
        if seed_file is None:
            print_warning("No seed file found, skipping seed step")
            return
        print_info(f"Running seed file: {seed_file.relative_to(backend)}")
        start = time.monotonic()
        result = subprocess.run(
            ["uv", "run", "python", str(seed_file.relative_to(backend))],
            cwd=backend,
            text=True,
        )
        elapsed = time.monotonic() - start
        console.print(f"[dim]Completed in {elapsed:.1f}s (exit code {result.returncode})[/dim]")
        if result.returncode == 0:
            print_success("Database seeded")
        else:
            print_error("Seed failed")
            raise typer.Exit(code=result.returncode)


@db_app.command()
def shell(
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
) -> None:
    """Open Django database shell."""
    backend = _resolve_backend(path or Path.cwd())
    result = _run_manage(backend, ["dbshell"])
    raise typer.Exit(code=result.returncode)


@db_app.command()
def dump(
    app_label: Annotated[
        str | None,
        typer.Option("--app", "-a", help="Dump specific Django app"),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
) -> None:
    """Dump database fixtures as JSON."""
    backend = _resolve_backend(path or Path.cwd())
    args = ["dumpdata", "--indent", "2"]
    if app_label:
        args.append(app_label)
    if output:
        args.extend(["--output", output])

    result = _run_manage(backend, args, capture=bool(output))
    if result.returncode == 0:
        if output:
            print_success(f"Fixtures dumped to {output}")
        else:
            print_success("Fixtures dumped")
    else:
        print_error("dumpdata failed")
        raise typer.Exit(code=result.returncode)


@db_app.command()
def load(
    fixture: Annotated[
        str,
        typer.Argument(help="Fixture file to load"),
    ],
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
) -> None:
    """Load fixtures into the database."""
    backend = _resolve_backend(path or Path.cwd())
    result = _run_manage(backend, ["loaddata", fixture])
    if result.returncode == 0:
        print_success(f"Fixture loaded: {fixture}")
    else:
        print_error(f"Failed to load fixture: {fixture}")
        raise typer.Exit(code=result.returncode)
