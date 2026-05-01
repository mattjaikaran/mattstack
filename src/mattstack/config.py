"""Configuration dataclasses and constants."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ProjectType(str, Enum):
    FULLSTACK = "fullstack"
    BACKEND_ONLY = "backend-only"
    FRONTEND_ONLY = "frontend-only"


class Variant(str, Enum):
    STARTER = "starter"
    B2B = "b2b"


class BackendFramework(str, Enum):
    DJANGO_NINJA = "django-ninja"
    DJANGO_MATT = "django-matt"


class FrontendFramework(str, Enum):
    REACT_VITE = "react-vite"
    REACT_VITE_STARTER = "react-vite-starter"
    REACT_RSBUILD = "react-rsbuild"
    REACT_RSBUILD_KIBO = "react-rsbuild-kibo"
    NEXTJS = "nextjs"


class DeploymentTarget(str, Enum):
    DOCKER = "docker"
    RAILWAY = "railway"
    RENDER = "render"
    FLY_IO = "fly-io"
    CLOUDFLARE = "cloudflare"
    DIGITAL_OCEAN = "digital-ocean"
    AWS = "aws"
    GCP = "gcp"
    HETZNER = "hetzner"
    SELF_HOSTED = "self-hosted"


REPO_URLS: dict[str, str] = {
    "django-ninja": "https://github.com/mattjaikaran/django-ninja-boilerplate.git",
    "django-matt": "https://github.com/mattjaikaran/django-matt-boilerplate.git",
    "react-vite": "https://github.com/mattjaikaran/react-vite-boilerplate.git",
    "react-vite-starter": "https://github.com/mattjaikaran/react-vite-starter.git",
    "react-rsbuild": "https://github.com/mattjaikaran/react-rsbuild-boilerplate.git",
    "react-rsbuild-kibo": "https://github.com/mattjaikaran/react-rsbuild-kibo-boilerplate.git",
    "nextjs": "https://github.com/mattjaikaran/nextjs-starter.git",
    "swift-ios": "https://github.com/mattjaikaran/swift-ios-starter.git",
}

DEFAULT_BRANCH = "main"


def get_repo_urls() -> dict[str, str]:
    """Get repo URLs merged with user config overrides."""
    from mattstack.user_config import get_user_repos

    urls = dict(REPO_URLS)
    urls.update(get_user_repos())
    return urls


def normalize_name(name: str) -> str:
    """Normalize project name: lowercase, hyphens, no special chars."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")


def to_python_package(name: str) -> str:
    """Convert project name to valid Python package name."""
    return normalize_name(name).replace("-", "_")


@dataclass
class ProjectConfig:
    """Full configuration for a project scaffold."""

    name: str
    path: Path
    project_type: ProjectType = ProjectType.FULLSTACK
    variant: Variant = Variant.STARTER
    frontend_framework: FrontendFramework = FrontendFramework.REACT_VITE
    backend_framework: BackendFramework = BackendFramework.DJANGO_NINJA
    include_ios: bool = False
    use_celery: bool = True
    use_redis: bool = True
    deployment: DeploymentTarget = DeploymentTarget.DOCKER
    init_git: bool = True
    author_name: str = ""
    author_email: str = ""
    dry_run: bool = False

    def __post_init__(self) -> None:
        self.name = normalize_name(self.name)
        if not self.name:
            raise ValueError("Project name cannot be empty")
        if isinstance(self.path, str):
            self.path = Path(self.path)
        # Frontend-only projects don't need backend features
        if self.project_type == ProjectType.FRONTEND_ONLY:
            self.use_celery = False
            self.use_redis = False
            self.include_ios = False
        # Celery requires Redis
        if self.use_celery and not self.use_redis:
            self.use_redis = True

    @property
    def python_package_name(self) -> str:
        return to_python_package(self.name)

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ").title()

    @property
    def has_backend(self) -> bool:
        return self.project_type in (ProjectType.FULLSTACK, ProjectType.BACKEND_ONLY)

    @property
    def has_frontend(self) -> bool:
        return self.project_type in (ProjectType.FULLSTACK, ProjectType.FRONTEND_ONLY)

    @property
    def is_fullstack(self) -> bool:
        return self.project_type == ProjectType.FULLSTACK

    @property
    def is_b2b(self) -> bool:
        return self.variant == Variant.B2B

    @property
    def backend_dir(self) -> Path:
        return self.path / "backend"

    @property
    def frontend_dir(self) -> Path:
        return self.path / "frontend"

    @property
    def ios_dir(self) -> Path:
        return self.path / "ios"

    @property
    def is_nextjs(self) -> bool:
        return self.frontend_framework == FrontendFramework.NEXTJS

    @property
    def is_django_matt(self) -> bool:
        return self.backend_framework == BackendFramework.DJANGO_MATT

    @property
    def backend_repo_key(self) -> str:
        return self.backend_framework.value

    @property
    def frontend_repo_key(self) -> str:
        return self.frontend_framework.value
