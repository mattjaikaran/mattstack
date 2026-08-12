"""Tests for mattstack dev command."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from mattstack.commands.dev import (
    _has_backend,
    _has_docker,
    _has_frontend,
    _parse_services,
    run_dev,
)


class TestHasBackend:
    def test_has_backend_when_pyproject_and_manage_exist(self, tmp_path: Path) -> None:
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (backend / "manage.py").write_text("")
        assert _has_backend(tmp_path) is True

    def test_no_backend_when_missing_pyproject(self, tmp_path: Path) -> None:
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / "manage.py").write_text("")
        assert _has_backend(tmp_path) is False

    def test_no_backend_when_missing_manage(self, tmp_path: Path) -> None:
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").write_text('[project]\nname = "test"\n')
        assert _has_backend(tmp_path) is False

    def test_no_backend_when_empty_dir(self, tmp_path: Path) -> None:
        assert _has_backend(tmp_path) is False


class TestHasFrontend:
    def test_has_frontend_when_dev_script_exists(self, tmp_path: Path) -> None:
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text(json.dumps({"scripts": {"dev": "vite"}}))
        assert _has_frontend(tmp_path) is True

    def test_no_frontend_when_no_dev_script(self, tmp_path: Path) -> None:
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}))
        assert _has_frontend(tmp_path) is False

    def test_no_frontend_when_no_package_json(self, tmp_path: Path) -> None:
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        assert _has_frontend(tmp_path) is False

    def test_no_frontend_when_invalid_json(self, tmp_path: Path) -> None:
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text("not json")
        assert _has_frontend(tmp_path) is False


class TestHasDocker:
    def test_has_docker_when_compose_exists(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")
        assert _has_docker(tmp_path) is True

    def test_no_docker_when_compose_missing(self, tmp_path: Path) -> None:
        assert _has_docker(tmp_path) is False


class TestParseServices:
    def test_none_returns_all(self) -> None:
        assert _parse_services(None) == {"docker", "backend", "frontend"}

    def test_empty_string_returns_all(self) -> None:
        assert _parse_services("") == {"docker", "backend", "frontend"}

    def test_single_service(self) -> None:
        assert _parse_services("backend") == {"backend"}

    def test_multiple_services(self) -> None:
        assert _parse_services("backend,frontend") == {"backend", "frontend"}

    def test_strips_whitespace_and_lowercase(self) -> None:
        assert _parse_services("  Backend ,  Frontend  ") == {"backend", "frontend"}

    def test_ignores_empty_parts(self) -> None:
        assert _parse_services("backend,,frontend") == {"backend", "frontend"}


class TestRunDev:
    def test_no_project_structure_exits_1(self, tmp_path: Path) -> None:
        """Empty dir: no backend, no frontend, no docker -> exit 1."""
        with pytest.raises(typer.Exit) as exc_info:
            run_dev(tmp_path)
        assert exc_info.value.exit_code == 1

    def test_only_docker_compose_tries_docker(self, tmp_path: Path) -> None:
        """With docker-compose.yml, should try docker (mocked to succeed)."""
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")
        with (
            patch("mattstack.commands.dev.docker_compose_available", return_value=True),
            patch("mattstack.commands.dev.docker_running", return_value=True),
            patch("mattstack.commands.dev.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
            run_dev(tmp_path)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "compose" in call_args

    def test_no_docker_flag_skips_docker(self, tmp_path: Path) -> None:
        """With --no-docker and only docker-compose, no services to start -> exit 1."""
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")
        with pytest.raises(typer.Exit) as exc_info:
            run_dev(tmp_path, no_docker=True)
        assert exc_info.value.exit_code == 1

    def test_nonexistent_path_exits_1(self, tmp_path: Path) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            run_dev(tmp_path / "nonexistent")
        assert exc_info.value.exit_code == 1
