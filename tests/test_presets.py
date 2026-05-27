"""Tests for presets module."""

from pathlib import Path

from mattstack.config import BackendFramework, FrontendFramework, ProjectType, Variant
from mattstack.presets import get_preset, list_presets


def test_list_presets():
    presets = list_presets()
    assert len(presets) == 24
    names = [p.name for p in presets]
    assert "starter-fullstack" in names
    assert "b2b-fullstack" in names
    assert "simple-frontend" in names
    assert "rsbuild-fullstack" in names
    assert "rsbuild-frontend" in names
    assert "kibo-fullstack" in names
    assert "kibo-frontend" in names
    assert "nextjs-fullstack" in names
    assert "nextjs-frontend" in names
    assert "matt-api" in names
    assert "matt-fullstack" in names
    assert "matt-b2b-fullstack" in names
    assert "fastapi-api" in names
    assert "fastapi-fullstack" in names
    assert "fastapi-b2b-fullstack" in names
    assert "fastapi-rsbuild-fullstack" in names
    assert "fastapi-nextjs-fullstack" in names
    assert "nestjs-api" in names
    assert "nestjs-fullstack" in names
    assert "nestjs-rsbuild-fullstack" in names
    assert "nestjs-nextjs-fullstack" in names


def test_get_preset():
    preset = get_preset("starter-fullstack")
    assert preset is not None
    assert preset.project_type == ProjectType.FULLSTACK
    assert preset.variant == Variant.STARTER


def test_get_preset_none():
    assert get_preset("nonexistent") is None


def test_preset_to_config(tmp_path: Path):
    preset = get_preset("b2b-api")
    assert preset is not None
    config = preset.to_config("my-api", tmp_path / "my-api")
    assert config.name == "my-api"
    assert config.project_type == ProjectType.BACKEND_ONLY
    assert config.variant == Variant.B2B


def test_simple_frontend_preset():
    preset = get_preset("simple-frontend")
    assert preset is not None
    assert preset.frontend_framework == FrontendFramework.REACT_VITE_STARTER
    assert preset.use_celery is False


def test_fastapi_api_preset(tmp_path: Path):
    preset = get_preset("fastapi-api")
    assert preset is not None
    assert preset.backend_framework == BackendFramework.FASTAPI
    assert preset.project_type == ProjectType.BACKEND_ONLY
    config = preset.to_config("my-api", tmp_path / "my-api")
    assert config.is_fastapi_backend is True
    assert config.backend_api_port == 8000
    assert config.use_celery is True


def test_fastapi_fullstack_preset():
    preset = get_preset("fastapi-fullstack")
    assert preset is not None
    assert preset.backend_framework == BackendFramework.FASTAPI
    assert preset.project_type == ProjectType.FULLSTACK
    assert preset.frontend_framework == FrontendFramework.REACT_VITE
