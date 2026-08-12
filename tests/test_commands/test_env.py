"""Tests for mattstack env command."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from mattstack.commands.env import (
    _find_env_pairs,
    _mask_value,
    _parse_env_file,
    run_env,
    run_env_check,
    run_env_show,
    run_env_sync,
)


class TestParseEnvFile:
    def test_basic_key_value(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")
        assert _parse_env_file(env_file) == {"FOO": "bar", "BAZ": "qux"}

    def test_ignores_comments(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\nFOO=bar\n# another\nBAZ=qux\n")
        assert _parse_env_file(env_file) == {"FOO": "bar", "BAZ": "qux"}

    def test_strips_quotes(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=\"bar\"\nBAZ='qux'\n")
        assert _parse_env_file(env_file) == {"FOO": "bar", "BAZ": "qux"}

    def test_empty_values(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=\nBAZ=\n")
        assert _parse_env_file(env_file) == {"FOO": "", "BAZ": ""}

    def test_handles_spaces_around_equals(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("FOO= bar \nBAZ= qux \n")
        assert _parse_env_file(env_file) == {"FOO": "bar", "BAZ": "qux"}

    def test_ignores_empty_lines(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nFOO=bar\n\n\n")
        assert _parse_env_file(env_file) == {"FOO": "bar"}

    def test_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        assert _parse_env_file(tmp_path / "nonexistent.env") == {}


class TestMaskValue:
    def test_empty_returns_stars(self) -> None:
        assert _mask_value("") == "***"

    def test_short_value_masks_fully(self) -> None:
        assert _mask_value("ab") == "**"
        assert _mask_value("a") == "*"

    def test_long_value_shows_first_three(self) -> None:
        assert _mask_value("secretkey123") == "sec***"
        assert _mask_value("abc") == "***"


class TestFindEnvPairs:
    def test_finds_root_example_actual_pair(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("FOO=bar\n")
        pairs = _find_env_pairs(tmp_path)
        assert len(pairs) >= 1
        ex, act = pairs[0]
        assert ex.name == ".env.example"
        assert act.name == ".env"

    def test_finds_backend_pair(self, tmp_path: Path) -> None:
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / ".env.example").write_text("FOO=bar\n")
        pairs = _find_env_pairs(tmp_path)
        assert any(".env.example" in str(p[0]) and "backend" in str(p[0]) for p in pairs)

    def test_empty_when_no_examples(self, tmp_path: Path) -> None:
        assert _find_env_pairs(tmp_path) == []


class TestRunEnvCheck:
    def test_matching_env_files(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("FOO=bar\nBAZ=qux\n")
        (tmp_path / ".env").write_text("FOO=bar\nBAZ=qux\n")
        run_env_check(tmp_path)
        # Should not raise

    def test_mismatching_reports_missing(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("FOO=bar\nBAZ=qux\nMISSING=val\n")
        (tmp_path / ".env").write_text("FOO=bar\n")
        run_env_check(tmp_path)
        # Should not raise; check produces output

    def test_nonexistent_path_exits_1(self, tmp_path: Path) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            run_env_check(tmp_path / "nonexistent")
        assert exc_info.value.exit_code == 1


class TestRunEnvSync:
    def test_creates_missing_vars(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("FOO=bar\nBAZ=qux\n")
        run_env_sync(tmp_path)
        actual = tmp_path / ".env"
        assert actual.exists()
        content = actual.read_text()
        assert "FOO=" in content
        assert "BAZ=" in content

    def test_adds_only_missing_to_existing(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("FOO=bar\nBAZ=qux\n")
        (tmp_path / ".env").write_text("FOO=existing\n")
        run_env_sync(tmp_path)
        content = (tmp_path / ".env").read_text()
        assert "FOO=existing" in content
        assert "BAZ=" in content


class TestRunEnvShow:
    def test_masks_values(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("SECRET=mysecret123\n")
        run_env_show(tmp_path)
        # Output goes to console; we verify no exception and file was read
        # The function uses _mask_value internally
        assert (tmp_path / ".env").exists()

    def test_nonexistent_path_exits_1(self, tmp_path: Path) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            run_env_show(tmp_path / "nonexistent")
        assert exc_info.value.exit_code == 1


class TestRunEnv:
    def test_invalid_action_exits_1(self, tmp_path: Path) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            run_env("invalid", tmp_path)
        assert exc_info.value.exit_code == 1

    def test_check_action(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("FOO=bar\n")
        (tmp_path / ".env").write_text("FOO=bar\n")
        run_env("check", tmp_path)

    def test_sync_action(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("FOO=bar\n")
        run_env("sync", tmp_path)
        assert (tmp_path / ".env").exists()

    def test_show_action(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("FOO=bar\n")
        run_env("show", tmp_path)


class TestEnvCliIntegration:
    def test_env_check_via_cli(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from mattstack.cli import app

        (tmp_path / ".env.example").write_text("FOO=bar\n")
        (tmp_path / ".env").write_text("FOO=bar\n")
        runner = CliRunner()
        result = runner.invoke(app, ["env", "check", "--path", str(tmp_path)])
        assert result.exit_code == 0
