"""Verify command: scope enforcement (design doc §6)."""

from __future__ import annotations

import fnmatch
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import typer

from mattstack.utils.console import print_error, print_success

DEFAULT_SCOPE_FILE = "SCOPE.md"


@dataclass
class ScopeResult:
    """Outcome of a scope check over changed files."""

    changed: list[str] = field(default_factory=list)
    in_scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)


def parse_scope_file(content: str) -> list[str]:
    """Parse a scope file into path/glob entries (comments and blanks ignored)."""
    entries: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def is_in_scope(file: str, scope: Sequence[str]) -> bool:
    """Return True when ``file`` matches any scope entry.

    A trailing ``/`` means directory-prefix match; otherwise glob, exact, or
    path-prefix matching applies.
    """
    for entry in scope:
        entry = entry.strip()
        if not entry:
            continue
        if entry.endswith("/"):
            if file.startswith(entry):
                return True
        elif fnmatch.fnmatch(file, entry) or file == entry or file.startswith(entry + "/"):
            return True
    return False


def verify_scope(changed: Sequence[str], scope: Sequence[str]) -> ScopeResult:
    """Split ``changed`` files into in-scope and out-of-scope buckets."""
    result = ScopeResult(changed=list(changed))
    for file in changed:
        bucket = result.in_scope if is_in_scope(file, scope) else result.out_of_scope
        bucket.append(file)
    return result


def changed_files(path: Path) -> list[str]:
    """Return modified and untracked files via ``git status --porcelain``."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    files: list[str] = []
    for line in proc.stdout.splitlines():
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        if path_part:
            files.append(path_part)
    return files


def run_verify(path: Path, scope_file: Path | None = None) -> None:
    """Enforce that changed files stay within the declared plan scope."""
    path = path.resolve()
    if not path.is_dir():
        print_error(f"Directory not found: {path}")
        raise typer.Exit(code=1)

    scope_path = scope_file or (path / DEFAULT_SCOPE_FILE)
    if not scope_path.is_absolute():
        scope_path = path / scope_path
    if not scope_path.exists():
        print_error(f"Scope file not found: {scope_path}")
        raise typer.Exit(code=1)

    scope = parse_scope_file(scope_path.read_text(encoding="utf-8"))
    if not scope:
        print_error(f"Scope file is empty: {scope_path}")
        raise typer.Exit(code=1)

    changed = changed_files(path)
    result = verify_scope(changed, scope)

    if result.out_of_scope:
        for file in result.out_of_scope:
            print_error(f"Out of scope: {file}")
        print_error(f"{len(result.out_of_scope)} file(s) outside the declared plan scope")
        raise typer.Exit(code=1)

    print_success(f"Scope check passed ({len(result.changed)} changed file(s) in scope)")
