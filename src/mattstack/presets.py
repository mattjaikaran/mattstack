"""Preset configurations for common project types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mattstack.config import (
    FrontendFramework,
    ProjectConfig,
    ProjectType,
    Variant,
)


@dataclass
class Preset:
    """A named preset configuration."""

    name: str
    description: str
    project_type: ProjectType
    variant: Variant
    frontend_framework: FrontendFramework = FrontendFramework.REACT_VITE
    include_ios: bool = False
    use_celery: bool = True

    def to_config(self, project_name: str, path: Path) -> ProjectConfig:
        return ProjectConfig(
            name=project_name,
            path=path,
            project_type=self.project_type,
            variant=self.variant,
            frontend_framework=self.frontend_framework,
            include_ios=self.include_ios,
            use_celery=self.use_celery,
        )


PRESETS: dict[str, Preset] = {
    "starter-fullstack": Preset(
        name="starter-fullstack",
        description="Standard fullstack monorepo (Django + React Vite TanStack)",
        project_type=ProjectType.FULLSTACK,
        variant=Variant.STARTER,
    ),
    "b2b-fullstack": Preset(
        name="b2b-fullstack",
        description="B2B fullstack with orgs/teams/roles (Django + React Vite)",
        project_type=ProjectType.FULLSTACK,
        variant=Variant.B2B,
    ),
    "starter-api": Preset(
        name="starter-api",
        description="Django API only (no frontend)",
        project_type=ProjectType.BACKEND_ONLY,
        variant=Variant.STARTER,
    ),
    "b2b-api": Preset(
        name="b2b-api",
        description="B2B Django API with orgs/teams/roles",
        project_type=ProjectType.BACKEND_ONLY,
        variant=Variant.B2B,
    ),
    "starter-frontend": Preset(
        name="starter-frontend",
        description="React Vite SPA with TanStack Router",
        project_type=ProjectType.FRONTEND_ONLY,
        variant=Variant.STARTER,
        use_celery=False,
    ),
    "simple-frontend": Preset(
        name="simple-frontend",
        description="Simpler React Vite SPA with React Router",
        project_type=ProjectType.FRONTEND_ONLY,
        variant=Variant.STARTER,
        frontend_framework=FrontendFramework.REACT_VITE_STARTER,
        use_celery=False,
    ),
    "rsbuild-fullstack": Preset(
        name="rsbuild-fullstack",
        description="Fullstack monorepo (Django API + React Rsbuild)",
        project_type=ProjectType.FULLSTACK,
        variant=Variant.STARTER,
        frontend_framework=FrontendFramework.REACT_RSBUILD,
    ),
    "rsbuild-frontend": Preset(
        name="rsbuild-frontend",
        description="React Rsbuild SPA with TanStack Router",
        project_type=ProjectType.FRONTEND_ONLY,
        variant=Variant.STARTER,
        frontend_framework=FrontendFramework.REACT_RSBUILD,
        use_celery=False,
    ),
    "kibo-fullstack": Preset(
        name="kibo-fullstack",
        description="Fullstack monorepo (Django API + React Rsbuild + Kibo UI)",
        project_type=ProjectType.FULLSTACK,
        variant=Variant.STARTER,
        frontend_framework=FrontendFramework.REACT_RSBUILD_KIBO,
    ),
    "kibo-frontend": Preset(
        name="kibo-frontend",
        description="React Rsbuild + Kibo UI SPA (dashboards, kanban, calendars)",
        project_type=ProjectType.FRONTEND_ONLY,
        variant=Variant.STARTER,
        frontend_framework=FrontendFramework.REACT_RSBUILD_KIBO,
        use_celery=False,
    ),
    "nextjs-fullstack": Preset(
        name="nextjs-fullstack",
        description="Fullstack monorepo (Django API + Next.js App Router)",
        project_type=ProjectType.FULLSTACK,
        variant=Variant.STARTER,
        frontend_framework=FrontendFramework.NEXTJS,
    ),
    "nextjs-frontend": Preset(
        name="nextjs-frontend",
        description="Next.js standalone (App Router, TypeScript, Tailwind)",
        project_type=ProjectType.FRONTEND_ONLY,
        variant=Variant.STARTER,
        frontend_framework=FrontendFramework.NEXTJS,
        use_celery=False,
    ),
}


def get_preset(name: str) -> Preset | None:
    return PRESETS.get(name)


def list_presets() -> list[Preset]:
    return list(PRESETS.values())


def get_all_presets() -> dict[str, Preset]:
    """Get all presets including user-defined ones."""
    from mattstack.user_config import get_user_presets

    all_presets = dict(PRESETS)
    user_presets = get_user_presets()
    for name, data in user_presets.items():
        if isinstance(data, dict):
            try:
                all_presets[name] = Preset(
                    name=name,
                    description=data.get("description", f"Custom preset: {name}"),
                    project_type=ProjectType(data.get("project_type", "fullstack")),
                    variant=Variant(data.get("variant", "starter")),
                    frontend_framework=FrontendFramework(
                        data.get("frontend_framework", "react-vite")
                    ),
                    include_ios=data.get("include_ios", False),
                    use_celery=data.get("use_celery", True),
                )
            except (ValueError, KeyError):
                continue  # Skip invalid presets
    return all_presets
