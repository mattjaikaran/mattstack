"""Tests for commands/hooks.py — Phase 21."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from mattstack.commands.hooks import hooks_app


# ---------------------------------------------------------------------------
# hooks install
# ---------------------------------------------------------------------------


class TestHooksInstall:
    def test_no_pre_commit_config_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(hooks_app, ["install", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert ".pre-commit-config.yaml" in result.output

    def test_pre_commit_not_available_exits_1(self, tmp_path: Path) -> None:
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        with patch("mattstack.commands.hooks.command_available", return_value=False):
            runner = CliRunner()
            result = runner.invoke(hooks_app, ["install", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "pre-commit is not installed" in result.output

    def test_pre_commit_install_failure_exits_1(self, tmp_path: Path) -> None:
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        failed = MagicMock()
        failed.returncode = 1
        failed.stderr = "something went wrong"
        with (
            patch("mattstack.commands.hooks.command_available", return_value=True),
            patch("mattstack.commands.hooks.subprocess.run", return_value=failed),
        ):
            runner = CliRunner()
            result = runner.invoke(hooks_app, ["install", "--path", str(tmp_path)])
        assert result.exit_code == 1

    def test_successful_install_exits_0(self, tmp_path: Path) -> None:
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        ok = MagicMock()
        ok.returncode = 0
        ok.stderr = ""
        with (
            patch("mattstack.commands.hooks.command_available", return_value=True),
            patch("mattstack.commands.hooks.subprocess.run", return_value=ok),
        ):
            runner = CliRunner()
            result = runner.invoke(hooks_app, ["install", "--path", str(tmp_path)])
        assert result.exit_code == 0

    def test_commitlint_config_installs_commit_msg_hook(self, tmp_path: Path) -> None:
        (tmp_path / ".pre-commit-config.yaml").write_text("repos:\n- commitlint\n")
        ok = MagicMock()
        ok.returncode = 0
        ok.stderr = ""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return ok

        with (
            patch("mattstack.commands.hooks.command_available", return_value=True),
            patch("mattstack.commands.hooks.subprocess.run", side_effect=fake_run),
        ):
            runner = CliRunner()
            result = runner.invoke(hooks_app, ["install", "--path", str(tmp_path)])
        assert result.exit_code == 0
        # second call should be commit-msg hook install
        assert any("commit-msg" in str(c) for c in calls)


# ---------------------------------------------------------------------------
# hooks status
# ---------------------------------------------------------------------------


class TestHooksStatus:
    def test_no_git_hooks_dir_exits_1(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(hooks_app, ["status", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "No .git/hooks directory" in result.output

    def test_no_hooks_installed_shows_not_installed(self, tmp_path: Path) -> None:
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        runner = CliRunner()
        result = runner.invoke(hooks_app, ["status", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "not installed" in result.output

    def test_installed_hook_shows_installed(self, tmp_path: Path) -> None:
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "pre-commit").write_text("#!/bin/sh\npre-commit run\n")
        runner = CliRunner()
        result = runner.invoke(hooks_app, ["status", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "installed" in result.output

    def test_no_config_shows_info_message(self, tmp_path: Path) -> None:
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        runner = CliRunner()
        result = runner.invoke(hooks_app, ["status", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "No .pre-commit-config.yaml found" in result.output

    def test_config_present_but_no_hooks_warns(self, tmp_path: Path) -> None:
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        runner = CliRunner()
        result = runner.invoke(hooks_app, ["status", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "hooks install" in result.output

    def test_pre_commit_source_detected(self, tmp_path: Path) -> None:
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "pre-commit").write_text("#!/bin/sh\npre-commit run --hook-stage pre-commit\n")
        runner = CliRunner()
        result = runner.invoke(hooks_app, ["status", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "pre-commit" in result.output


# ---------------------------------------------------------------------------
# hooks run
# ---------------------------------------------------------------------------


class TestHooksRun:
    def test_no_pre_commit_exits_1(self, tmp_path: Path) -> None:
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        with patch("mattstack.commands.hooks.command_available", return_value=False):
            runner = CliRunner()
            result = runner.invoke(hooks_app, ["run", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "pre-commit is not installed" in result.output

    def test_no_config_exits_1(self, tmp_path: Path) -> None:
        with patch("mattstack.commands.hooks.command_available", return_value=True):
            runner = CliRunner()
            result = runner.invoke(hooks_app, ["run", "--path", str(tmp_path)])
        assert result.exit_code == 1

    def test_all_hooks_pass_exits_0(self, tmp_path: Path) -> None:
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        ok = MagicMock()
        ok.returncode = 0
        with (
            patch("mattstack.commands.hooks.command_available", return_value=True),
            patch("mattstack.commands.hooks.subprocess.run", return_value=ok),
        ):
            runner = CliRunner()
            result = runner.invoke(hooks_app, ["run", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "All hooks passed" in result.output

    def test_failing_hooks_exits_1(self, tmp_path: Path) -> None:
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        fail = MagicMock()
        fail.returncode = 1
        with (
            patch("mattstack.commands.hooks.command_available", return_value=True),
            patch("mattstack.commands.hooks.subprocess.run", return_value=fail),
        ):
            runner = CliRunner()
            result = runner.invoke(hooks_app, ["run", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "Some hooks failed" in result.output
