#!/usr/bin/env python3
"""Gauntlet constraint-tools runner for mattstack-cli.

Gates:
    1. FORMAT — ruff format --check
    2. LINT — ruff check (50+ rules)
    3. TYPECHECK — mypy
    4. SECURITY — bandit
    5. ARCH — scripts/check_architecture.py
    6. FILELENGTH — scripts/check_file_length.py (400 lines)
    7. TEST — pytest with coverage
    8. MUTATION — mutmut (skipped in quick mode)
    9. AUDIT — pip-audit (skipped in quick mode)
   10. INSTALL — pip install -e . check

Usage:
    python scripts/gauntlet.py          # full gauntlet
    python scripts/gauntlet.py --quick  # skip mutation + audit
    python scripts/gauntlet.py --gate lint  # run one gate
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"


@dataclass
class Gate:
    name: str
    description: str
    run: Callable[[], bool] = field(repr=False)
    quick: bool = True


# ---------------------------------------------------------------------------
# gate implementations
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str]:
    """Run a command, return (exit_code, combined_output)."""
    result = subprocess.run(
        cmd,
        cwd=cwd or PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout + result.stderr


def _gate_ruff_format() -> bool:
    """Gate 1: ruff format --check."""
    bin_ = shutil.which("uv") or "uv"
    code, out = _run([bin_, "run", "ruff", "format", "--check", str(SRC_DIR), str(TESTS_DIR)])
    if code != 0:
        print(out)
    return code == 0


def _gate_ruff_lint() -> bool:
    """Gate 2: ruff check."""
    bin_ = shutil.which("uv") or "uv"
    code, out = _run([bin_, "run", "ruff", "check", str(SRC_DIR), str(TESTS_DIR)])
    if code != 0:
        print(out)
    return code == 0


def _gate_mypy() -> bool:
    """Gate 3: mypy typecheck."""
    bin_ = shutil.which("uv") or "uv"
    code, out = _run([bin_, "run", "mypy", str(SRC_DIR)])
    if code != 0:
        print(out)
    return code == 0


def _gate_bandit() -> bool:
    """Gate 4: bandit security scan."""
    bin_ = shutil.which("uv") or "uv"
    code, out = _run([bin_, "run", "bandit", "-r", str(SRC_DIR), "-c", "pyproject.toml"])
    if code != 0:
        print(out)
    return code == 0


def _gate_arch() -> bool:
    """Gate 5: architecture layer check."""
    arch_script = PROJECT_ROOT / "scripts" / "check_architecture.py"
    code, out = _run([sys.executable, str(arch_script)])
    if code != 0:
        print(out)
    return code == 0


def _gate_file_length() -> bool:
    """Gate 6: file length check."""
    fl_script = PROJECT_ROOT / "scripts" / "check_file_length.py"
    code, out = _run([sys.executable, str(fl_script)])
    if code != 0:
        print(out)
    return code == 0


def _gate_test() -> bool:
    """Gate 7: pytest with coverage."""
    bin_ = shutil.which("uv") or "uv"
    code, out = _run(
        [bin_, "run", "pytest", "--cov", "mattstack", "--cov-report=term-missing", "-x", "-q"],
        timeout=300,
    )
    if code != 0:
        print(out)
    return code == 0


def _gate_mutation() -> bool:
    """Gate 8: mutmut mutation testing."""
    bin_ = shutil.which("uv") or "uv"
    code, out = _run([bin_, "run", "mutmut", "run"], timeout=600)
    if code != 0:
        print(out)
    return code == 0


def _gate_audit() -> bool:
    """Gate 9: pip-audit dependency audit."""
    bin_ = shutil.which("uv") or "uv"
    code, out = _run([bin_, "run", "pip-audit"])
    if code != 0:
        print(out)
    return code == 0


def _gate_install() -> bool:
    """Gate 10: pip install -e . check."""
    bin_ = shutil.which("uv") or "uv"
    code, out = _run([bin_, "pip", "install", "-e", "."])
    if code != 0:
        print(out)
    return code == 0


# ---------------------------------------------------------------------------
# gate registry
# ---------------------------------------------------------------------------

GATES: list[Gate] = [
    Gate("format", "ruff format --check", quick=True, run=_gate_ruff_format),
    Gate("lint", "ruff check (50+ rules)", quick=True, run=_gate_ruff_lint),
    Gate("typecheck", "mypy strict", quick=True, run=_gate_mypy),
    Gate("security", "bandit scan", quick=True, run=_gate_bandit),
    Gate("arch", "layer enforcement", quick=True, run=_gate_arch),
    Gate("filelength", "400-line limit", quick=True, run=_gate_file_length),
    Gate("test", "pytest + coverage", quick=True, run=_gate_test),
    Gate("mutation", "mutmut", quick=False, run=_gate_mutation),
    Gate("audit", "pip-audit", quick=False, run=_gate_audit),
    Gate("install", "pip install check", quick=True, run=_gate_install),
]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="mattstack-cli gauntlet runner")
    parser.add_argument("--quick", action="store_true", help="Skip mutation and audit gates")
    parser.add_argument("--gate", type=str, help="Run a single gate by name")
    args = parser.parse_args()

    if args.gate:
        gate_map = {g.name: g for g in GATES}
        if args.gate not in gate_map:
            print(f"Unknown gate: {args.gate}")
            print(f"Available: {', '.join(gate_map)}")
            sys.exit(2)
        gates = [gate_map[args.gate]]
    else:
        gates = [g for g in GATES if not args.quick or g.quick]

    print(
        f"Running {'quick ' if args.quick and not args.gate else ''}gauntlet — {len(gates)} gates\n"
    )

    passed = 0
    failed = 0
    for gate in gates:
        status = "PASS" if gate.run() else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {gate.name}: {gate.description}")

    print(f"\n{passed} passed, {failed} failed, {len(gates)} total")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
