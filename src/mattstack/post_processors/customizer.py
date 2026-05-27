"""Post-processor to customize cloned repos (rename, rebrand)."""

from __future__ import annotations

import json

from mattstack.config import ProjectConfig
from mattstack.utils.console import print_info


def customize_backend(config: ProjectConfig) -> None:
    """Rename the backend project to match the project name."""
    if config.is_nestjs_backend:
        _customize_nestjs_backend(config)
    elif config.is_fastapi_backend:
        _customize_fastapi_backend(config)
    else:
        _customize_django_backend(config)


def _customize_django_backend(config: ProjectConfig) -> None:
    """Rename a Django backend project."""
    pyproject = config.backend_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        content = content.replace(
            'name = "django-ninja-boilerplate"',
            f'name = "{config.name}-backend"',
        )
        content = content.replace(
            'name = "django_ninja_boilerplate"',
            f'name = "{config.python_package_name}_backend"',
        )
        pyproject.write_text(content)
        print_info(f"Renamed backend to {config.name}-backend")

    # Remove boilerplate cli/ dir if somehow still present
    cli_dir = config.backend_dir / "cli"
    if cli_dir.exists():
        import shutil

        shutil.rmtree(cli_dir)


def _customize_fastapi_backend(config: ProjectConfig) -> None:
    """Rename a FastAPI backend project."""
    pyproject = config.backend_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        content = content.replace(
            'name = "fastapi-postgres-boilerplate"',
            f'name = "{config.name}-backend"',
        )
        pyproject.write_text(content)
        print_info(f"Renamed backend to {config.name}-backend")


def _customize_nestjs_backend(config: ProjectConfig) -> None:
    """Rename a NestJS backend project via package.json."""
    package_json = config.backend_dir / "package.json"
    if package_json.exists():
        data = json.loads(package_json.read_text())
        data["name"] = f"{config.name}-backend"
        data["description"] = f"{config.display_name} API (NestJS)"
        package_json.write_text(json.dumps(data, indent=2) + "\n")
        print_info(f"Renamed backend to {config.name}-backend")


def customize_frontend(config: ProjectConfig) -> None:
    """Rename the frontend project to match the project name."""
    package_json = config.frontend_dir / "package.json"
    if package_json.exists():
        data = json.loads(package_json.read_text())
        data["name"] = f"{config.name}-frontend"
        package_json.write_text(json.dumps(data, indent=2) + "\n")
        print_info(f"Renamed frontend to {config.name}-frontend")
