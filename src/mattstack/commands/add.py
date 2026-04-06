"""Add command: expand existing projects with new layers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer

from mattstack.config import (
    FrontendFramework,
    ProjectConfig,
    ProjectType,
    get_repo_urls,
)
from mattstack.utils.console import (
    console,
    create_progress,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from mattstack.utils.git import clone_repo, remove_git_history

VALID_COMPONENTS = ("frontend", "backend", "ios")


def _detect_project(path: Path) -> dict:
    """Detect what components exist in a project directory."""
    return {
        "has_backend": (path / "backend" / "pyproject.toml").exists(),
        "has_frontend": (path / "frontend" / "package.json").exists(),
        "has_ios": (path / "ios").exists(),
        "name": path.name,
    }


def _build_config(
    path: Path,
    detected: dict,
    adding: str,
    framework: str | None,
) -> ProjectConfig:
    """Build a ProjectConfig that reflects the post-add state."""
    has_backend = detected["has_backend"] or adding == "backend"
    has_frontend = detected["has_frontend"] or adding == "frontend"
    has_ios = detected["has_ios"] or adding == "ios"

    if has_backend and has_frontend:
        project_type = ProjectType.FULLSTACK
    elif has_backend:
        project_type = ProjectType.BACKEND_ONLY
    else:
        project_type = ProjectType.FRONTEND_ONLY

    fw = FrontendFramework(framework) if framework else FrontendFramework.REACT_VITE

    return ProjectConfig(
        name=detected["name"],
        path=path,
        project_type=project_type,
        frontend_framework=fw,
        include_ios=has_ios,
        init_git=False,
    )


def _clone_component(component: str, config: ProjectConfig, *, dry_run: bool) -> bool:
    """Clone the appropriate repo for the given component."""
    if component == "frontend":
        repo_key = config.frontend_repo_key
        dest = config.frontend_dir
    elif component == "backend":
        repo_key = config.backend_repo_key
        dest = config.backend_dir
    elif component == "ios":
        repo_key = "swift-ios"
        dest = config.ios_dir
    else:
        print_error(f"Unknown component: {component}")
        return False

    url = get_repo_urls()[repo_key]

    if dry_run:
        print_info(f"[dry-run] Would clone {url} into {dest.name}/")
        return True

    if not clone_repo(url, dest):
        return False
    remove_git_history(dest)
    print_success(f"Cloned {component} into {dest.name}/")
    return True


def _customize_component(component: str, config: ProjectConfig, *, dry_run: bool) -> bool:
    """Run post-processing customization for the new component."""
    if dry_run:
        print_info(f"[dry-run] Would customize {component}")
        return True

    if component == "frontend":
        from mattstack.post_processors.customizer import customize_frontend
        from mattstack.post_processors.frontend_config import setup_frontend_monorepo

        customize_frontend(config)
        if config.has_backend:
            setup_frontend_monorepo(config)
    elif component == "backend":
        from mattstack.post_processors.customizer import customize_backend

        customize_backend(config)
    # iOS has no post-processing beyond the clone

    return True


def _update_root_files(config: ProjectConfig, *, dry_run: bool) -> bool:
    """Re-generate root files to reflect the new project structure."""
    from mattstack.templates.docker_compose import generate_docker_compose
    from mattstack.templates.root_env import generate_env_example
    from mattstack.templates.root_makefile import generate_makefile
    from mattstack.templates.root_readme import generate_readme

    files: list[tuple[str, str]] = [
        ("Makefile", generate_makefile(config)),
        (".env.example", generate_env_example(config)),
        ("README.md", generate_readme(config)),
    ]

    # Only generate docker-compose if the project has a backend
    if config.has_backend:
        files.append(("docker-compose.yml", generate_docker_compose(config)))

    for filename, content in files:
        filepath = config.path / filename
        if dry_run:
            verb = "overwrite" if filepath.exists() else "create"
            print_info(f"[dry-run] Would {verb} {filename}")
            continue
        if filepath.exists():
            print_warning(f"Overwriting {filename}")
        filepath.write_text(content)

    return True


def _print_next_steps(component: str, config: ProjectConfig) -> None:
    """Print instructions for what to do after adding a component."""
    console.print()
    print_success(f"Added {component} to '{config.name}'!")
    console.print()
    console.print("[bold]Next steps:[/bold]")

    if component == "frontend":
        console.print("  [cyan]cd frontend && bun install[/cyan]")
        console.print("  [cyan]make frontend-dev[/cyan]  # http://localhost:3000")
    elif component == "backend":
        console.print("  [cyan]cd backend && uv sync[/cyan]")
        console.print("  [cyan]make up[/cyan]              # Start Docker services")
        console.print("  [cyan]make backend-migrate[/cyan]")
        console.print("  [cyan]make backend-superuser[/cyan]")
        console.print("  [cyan]make backend-dev[/cyan]     # http://localhost:8000")
    elif component == "ios":
        console.print("  [cyan]Open ios/ in Xcode[/cyan]")
        console.print("  [cyan]Update API base URL in the iOS project[/cyan]")

    console.print()


def run_add(
    component: str,
    project_path: Path,
    framework: str | None = None,
    dry_run: bool = False,
) -> None:
    """Add a new component (frontend, backend, ios) to an existing project."""
    # Validate component name
    if component not in VALID_COMPONENTS:
        print_error(
            f"Invalid component: '{component}'. Must be one of: {', '.join(VALID_COMPONENTS)}"
        )
        raise typer.Exit(code=1)

    # Validate framework option
    if framework:
        valid_frameworks = [f.value for f in FrontendFramework]
        if framework not in valid_frameworks:
            print_error(
                f"Invalid framework '{framework}'. "
                f"Valid: {', '.join(valid_frameworks)}"
            )
            raise typer.Exit(code=1)

    # Validate project path exists
    if not project_path.is_dir():
        print_error(f"Project directory not found: {project_path}")
        raise typer.Exit(code=1)

    # Detect current state
    detected = _detect_project(project_path)

    # Check if the component already exists
    component_exists = {
        "frontend": detected["has_frontend"],
        "backend": detected["has_backend"],
        "ios": detected["has_ios"],
    }
    if component_exists[component]:
        print_error(f"Project already has a {component} component")
        raise typer.Exit(code=1)

    # Build config reflecting the post-add state
    config = _build_config(project_path, detected, component, framework)

    # Execute steps with progress bar
    steps: list[tuple[str, Callable[[], bool]]] = [
        (f"Cloning {component}", lambda: _clone_component(component, config, dry_run=dry_run)),
        (
            f"Customizing {component}",
            lambda: _customize_component(component, config, dry_run=dry_run),
        ),
        ("Updating root files", lambda: _update_root_files(config, dry_run=dry_run)),
    ]

    with create_progress() as progress:
        task = progress.add_task(f"Adding {component}...", total=len(steps))
        for description, step_fn in steps:
            progress.update(task, description=description)
            result = step_fn()
            if result is False:
                print_error(f"Failed at step: {description}")
                raise typer.Exit(code=1)
            progress.advance(task)

    _print_next_steps(component, config)
