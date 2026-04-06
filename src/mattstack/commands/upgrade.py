"""Upgrade command: pull latest boilerplate changes into existing project."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import typer
from rich.table import Table

from mattstack.config import get_repo_urls
from mattstack.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from mattstack.utils.git import clone_repo, remove_git_history

# Map component directory names to upstream repo keys
COMPONENT_REPOS: dict[str, str] = {
    "backend": "django-ninja",
    "frontend": "react-vite",
}

# Files that indicate Next.js frontend (checked during upgrade to pick correct repo)
NEXTJS_MARKERS = {"next.config.ts", "next.config.js", "next.config.mjs"}

# Files that indicate Rsbuild frontend
RSBUILD_MARKERS = {"rsbuild.config.ts", "rsbuild.config.js", "rsbuild.config.mjs"}

# Files that are typically user-customized and should never be overwritten
SKIP_FILES: set[str] = {"README.md", ".env", ".env.local", "CLAUDE.md"}

# Directories to ignore when comparing file trees
IGNORE_DIRS: set[str] = {".git", "__pycache__", "node_modules", ".venv", ".ruff_cache"}


@dataclass
class FileChange:
    """A single file change detected between upstream and local."""

    path: str  # relative path within component
    status: str  # "new", "modified", "deleted"


@dataclass
class UpgradeReport:
    """Summary of changes for a single component upgrade."""

    component: str
    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    applied: int = 0
    skipped: int = 0

    @property
    def total_changes(self) -> int:
        return len(self.new_files) + len(self.modified_files) + len(self.deleted_files)

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0


def run_upgrade(
    path: Path,
    *,
    component: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Main upgrade entry point. Compares project against fresh boilerplate clones."""
    project_path = path.resolve()

    if not project_path.is_dir():
        print_error(f"Not a directory: {project_path}")
        raise typer.Exit(code=1)

    # Detect which components exist in the project
    components = _detect_components(project_path)
    if not components:
        print_error("No recognized components found (backend/frontend)")
        raise typer.Exit(code=1)

    # Validate requested component
    if component:
        if component not in COMPONENT_REPOS:
            valid = ", ".join(sorted(COMPONENT_REPOS.keys()))
            print_error(f"Unknown component: '{component}'. Valid: {valid}")
            raise typer.Exit(code=1)
        if component not in components:
            print_error(f"Component '{component}' not found in project at {project_path}")
            raise typer.Exit(code=1)
        components = [component]

    if dry_run:
        console.print(f"\n[bold cyan]Upgrade (dry run):[/bold cyan] {project_path}\n")
    else:
        console.print(f"\n[bold cyan]Upgrading:[/bold cyan] {project_path}\n")

    reports: list[UpgradeReport] = []
    for comp in components:
        if comp == "frontend":
            repo_key = _detect_frontend_repo_key(project_path)
        else:
            repo_key = COMPONENT_REPOS[comp]
        report = _upgrade_component(
            project_path,
            comp,
            repo_key,
            dry_run=dry_run,
            force=force,
        )
        reports.append(report)

    # Print summary
    _print_summary(reports, dry_run=dry_run)


def _detect_components(path: Path) -> list[str]:
    """Return list of components that exist in the project."""
    components: list[str] = []
    if (path / "backend" / "pyproject.toml").exists():
        components.append("backend")
    if (path / "frontend" / "package.json").exists():
        components.append("frontend")
    return components


def _is_kibo_project(frontend_dir: Path) -> bool:
    """Check if a rsbuild project uses Kibo UI (has @dnd-kit or kibo in package.json)."""
    pkg = frontend_dir / "package.json"
    if not pkg.exists():
        return False
    try:
        import json

        data = json.loads(pkg.read_text(encoding="utf-8"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        return "@dnd-kit/core" in deps or "recharts" in deps
    except (json.JSONDecodeError, OSError):
        return False


def _detect_frontend_repo_key(project_path: Path) -> str:
    """Detect which frontend boilerplate repo to compare against."""
    frontend_dir = project_path / "frontend"
    if any((frontend_dir / marker).exists() for marker in NEXTJS_MARKERS):
        return "nextjs"
    if any((frontend_dir / marker).exists() for marker in RSBUILD_MARKERS):
        if _is_kibo_project(frontend_dir):
            return "react-rsbuild-kibo"
        return "react-rsbuild"
    return "react-vite"


def _upgrade_component(
    project_path: Path,
    component: str,
    repo_key: str,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> UpgradeReport:
    """Upgrade a single component by comparing with a fresh clone."""
    report = UpgradeReport(component=component)
    target_dir = project_path / component

    print_info(f"Checking {component} against upstream ({repo_key})...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / component
        url = get_repo_urls()[repo_key]

        if not clone_repo(url, tmp_path):
            print_error(f"Failed to clone {repo_key} boilerplate")
            return report

        remove_git_history(tmp_path)

        # Compare fresh clone against existing project component
        new_files, modified_files, deleted_files = _compare_directories(tmp_path, target_dir)

        report.new_files = new_files
        report.modified_files = modified_files
        report.deleted_files = deleted_files

        if not report.has_changes:
            print_success(f"{component}: already up to date")
            return report

        # Print change table
        _print_changes(report)

        if dry_run:
            return report

        # Apply new files (always)
        for rel_path in new_files:
            src_file = tmp_path / rel_path
            dst_file = target_dir / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            report.applied += 1

        # Apply modified files only with --force
        if force:
            for rel_path in modified_files:
                src_file = tmp_path / rel_path
                dst_file = target_dir / rel_path
                shutil.copy2(src_file, dst_file)
                report.applied += 1
        else:
            report.skipped += len(modified_files)
            if modified_files:
                print_warning(
                    f"{len(modified_files)} modified file(s) skipped. Use --force to overwrite."
                )

        # Deleted files are always ignored (just reported)

    return report


def _compare_directories(source: Path, target: Path) -> tuple[list[str], list[str], list[str]]:
    """Compare source (fresh clone) with target (existing project).

    Returns (new_files, modified_files, deleted_files) as relative path strings.
    """
    new_files: list[str] = []
    modified_files: list[str] = []

    # Walk source to find new/modified files
    for src_file in sorted(source.rglob("*")):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(source)

        # Skip ignored directories
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        # Skip user-customized files
        if rel.name in SKIP_FILES:
            continue

        target_file = target / rel
        if not target_file.exists():
            new_files.append(str(rel))
        elif src_file.read_bytes() != target_file.read_bytes():
            modified_files.append(str(rel))

    # Walk target to find deleted files (in project but not in fresh clone)
    deleted_files: list[str] = []
    for tgt_file in sorted(target.rglob("*")):
        if tgt_file.is_dir():
            continue
        rel = tgt_file.relative_to(target)

        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if rel.name in SKIP_FILES:
            continue

        if not (source / rel).exists():
            deleted_files.append(str(rel))

    return new_files, modified_files, deleted_files


def _print_changes(report: UpgradeReport) -> None:
    """Print a Rich table of detected changes for a component."""
    table = Table(
        title=f"{report.component} changes",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Status", style="bold", width=10)
    table.add_column("File")

    for f in report.new_files:
        table.add_row("[green]new[/green]", f)
    for f in report.modified_files:
        table.add_row("[yellow]modified[/yellow]", f)
    for f in report.deleted_files:
        table.add_row("[red]deleted[/red]", f)

    console.print(table)
    console.print()


def _print_summary(reports: list[UpgradeReport], *, dry_run: bool = False) -> None:
    """Print final summary across all components."""
    total_new = sum(len(r.new_files) for r in reports)
    total_modified = sum(len(r.modified_files) for r in reports)
    total_deleted = sum(len(r.deleted_files) for r in reports)
    total_applied = sum(r.applied for r in reports)
    total_skipped = sum(r.skipped for r in reports)

    if not any(r.has_changes for r in reports):
        print_success("All components are up to date")
        return

    console.print("[bold]Summary:[/bold]")
    console.print(f"  New files:      {total_new}")
    console.print(f"  Modified files: {total_modified}")
    console.print(f"  Deleted files:  {total_deleted} (ignored)")

    if not dry_run:
        console.print(f"  Applied:        {total_applied}")
        if total_skipped:
            console.print(f"  Skipped:        {total_skipped}")
    else:
        print_info("Dry run complete. No files were changed.")

    console.print()
