"""Package manager abstraction — detect and wrap bun/npm/yarn/pnpm."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class PackageManager(StrEnum):
    BUN = "bun"
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"


LOCKFILE_MAP: dict[str, PackageManager] = {
    "bun.lockb": PackageManager.BUN,
    "bun.lock": PackageManager.BUN,
    "package-lock.json": PackageManager.NPM,
    "yarn.lock": PackageManager.YARN,
    "pnpm-lock.yaml": PackageManager.PNPM,
}

DEFAULT_PM = PackageManager.BUN


@dataclass
class PMCommand:
    """Resolved package manager command with args."""

    program: str
    args: list[str]

    @property
    def full(self) -> list[str]:
        return [self.program, *self.args]

    def __str__(self) -> str:
        return " ".join(self.full)


def detect_package_manager(project_path: Path) -> PackageManager:
    """Detect package manager from lockfiles in project or frontend/ subdirectory."""
    search_dirs = [project_path]
    frontend_dir = project_path / "frontend"
    if frontend_dir.is_dir():
        search_dirs.insert(0, frontend_dir)

    for d in search_dirs:
        for lockfile, pm in LOCKFILE_MAP.items():
            if (d / lockfile).exists():
                return pm

    return DEFAULT_PM


def _get_user_pm_override() -> PackageManager | None:
    """Check user config for a package_manager override."""
    try:
        from mattstack.user_config import load_user_config

        config = load_user_config()
        pm_value = config.get("defaults", {}).get("package_manager")  # type: ignore
        if pm_value and isinstance(pm_value, str):
            return PackageManager(pm_value)
    except (ValueError, ImportError):
        pass
    return None


def resolve_package_manager(
    project_path: Path,
    override: str | None = None,
) -> PackageManager:
    """Resolve which package manager to use (explicit > user config > lockfile > bun)."""
    if override:
        try:
            return PackageManager(override)
        except ValueError:
            pass

    user_pm = _get_user_pm_override()
    if user_pm:
        return user_pm

    return detect_package_manager(project_path)


def build_add_cmd(pm: PackageManager, packages: list[str], *, dev: bool = False) -> PMCommand:
    """Build an 'add package' command."""
    match pm:
        case PackageManager.BUN:
            args = ["add", *packages]
            if dev:
                args.insert(1, "-d")
        case PackageManager.NPM:
            args = ["install", *packages]
            if dev:
                args.append("--save-dev")
        case PackageManager.YARN:
            args = ["add", *packages]
            if dev:
                args.append("--dev")
        case PackageManager.PNPM:
            args = ["add", *packages]
            if dev:
                args.append("-D")
    return PMCommand(program=pm.value, args=args)


def build_remove_cmd(pm: PackageManager, packages: list[str]) -> PMCommand:
    """Build a 'remove package' command."""
    verb = "uninstall" if pm == PackageManager.NPM else "remove"
    return PMCommand(program=pm.value, args=[verb, *packages])


def build_install_cmd(pm: PackageManager) -> PMCommand:
    """Build an 'install all deps' command."""
    return PMCommand(program=pm.value, args=["install"])


def build_run_cmd(
    pm: PackageManager, script: str, extra_args: list[str] | None = None
) -> PMCommand:
    """Build a 'run script' command."""
    args = ["run", script]
    if extra_args:
        args.extend(extra_args)
    return PMCommand(program=pm.value, args=args)


def build_exec_cmd(
    pm: PackageManager, binary: str, extra_args: list[str] | None = None
) -> PMCommand:
    """Build an 'exec binary' command (npx/bunx/pnpm exec/yarn dlx)."""
    match pm:
        case PackageManager.BUN:
            prog, args = "bunx", [binary]
        case PackageManager.NPM:
            prog, args = "npx", [binary]
        case PackageManager.YARN:
            prog, args = "yarn", ["dlx", binary]
        case PackageManager.PNPM:
            prog, args = "pnpm", ["dlx", binary]
    if extra_args:
        args.extend(extra_args)
    return PMCommand(program=prog, args=args)


def run_pm_command(cmd: PMCommand, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Execute a package manager command, streaming output."""
    return subprocess.run(
        cmd.full,
        cwd=cwd,
        text=True,
        capture_output=False,
    )
