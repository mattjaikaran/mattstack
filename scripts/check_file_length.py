#!/usr/bin/env python3
"""Check that no Python file under src/ exceeds MAX_LINES.

Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

MAX_LINES = 400


def main() -> int:
    violations: list[tuple[Path, int]] = []

    for py_file in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in str(py_file) or ".egg-info" in str(py_file):
            continue

        try:
            line_count = sum(1 for _ in py_file.open(encoding="utf-8"))
        except Exception:
            continue

        if line_count > MAX_LINES:
            violations.append((py_file, line_count))

    if violations:
        exceed = len(violations)
        print(f"Files exceeding {MAX_LINES} lines ({exceed}):")
        for path, count in violations:
            print(f"  {path.relative_to(PROJECT_ROOT)} ({count} lines)")
        return 1

    print(f"File length check passed — no file exceeds {MAX_LINES} lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
