"""Tests for mattstack verify --scope (scope enforcement)."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from mattstack.commands.verify import (
    is_in_scope,
    parse_scope_file,
    run_verify,
    verify_scope,
)


def test_parse_scope_file() -> None:
    content = "# comment\n\nsrc/mattstack/\ntests/\n  \ndocs/plans/*.md\n"
    assert parse_scope_file(content) == ["src/mattstack/", "tests/", "docs/plans/*.md"]


def test_is_in_scope_dir_prefix() -> None:
    scope = ["src/mattstack/"]
    assert is_in_scope("src/mattstack/cli.py", scope) is True
    assert is_in_scope("docs/readme.md", scope) is False


def test_is_in_scope_glob() -> None:
    scope = ["docs/plans/*.md"]
    assert is_in_scope("docs/plans/plan.md", scope) is True
    assert is_in_scope("docs/plans/plan.txt", scope) is False


def test_is_in_scope_exact() -> None:
    assert is_in_scope("pyproject.toml", ["pyproject.toml"]) is True
    assert is_in_scope("pyproject.toml", ["pyproject.yaml"]) is False


def test_verify_scope_splits() -> None:
    result = verify_scope(
        ["src/mattstack/cli.py", "README.md"],
        ["src/mattstack/"],
    )
    assert result.in_scope == ["src/mattstack/cli.py"]
    assert result.out_of_scope == ["README.md"]


def test_run_verify_passes(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "SCOPE.md").write_text("src/\n", encoding="utf-8")
    monkeypatch.setattr(
        "mattstack.commands.verify.changed_files", lambda p: ["src/a.py", "src/b.py"]
    )

    run_verify(tmp_path)


def test_run_verify_fails_on_out_of_scope(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "SCOPE.md").write_text("src/\n", encoding="utf-8")
    monkeypatch.setattr(
        "mattstack.commands.verify.changed_files",
        lambda p: ["src/a.py", "README.md"],
    )

    with pytest.raises(typer.Exit) as exc:
        run_verify(tmp_path)

    assert exc.value.exit_code == 1


def test_run_verify_missing_scope_file(tmp_path: Path) -> None:
    with pytest.raises(typer.Exit) as exc:
        run_verify(tmp_path)

    assert exc.value.exit_code == 1
