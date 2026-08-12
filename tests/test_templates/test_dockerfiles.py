"""Tests for consolidated Dockerfile templates."""

from __future__ import annotations

from mattstack.config import BackendFramework, FrontendFramework, ProjectConfig
from mattstack.templates.dockerfiles import (
    generate_backend_dockerfile,
    generate_frontend_dev_dockerfile,
    generate_frontend_dockerfile,
    generate_frontend_nginx_conf,
)


def _config(backend: BackendFramework, frontend: FrontendFramework) -> ProjectConfig:
    return ProjectConfig(
        name="test-proj",
        path="/tmp/test-proj",
        backend_framework=backend,
        frontend_framework=frontend,
    )


def test_backend_dockerfile_django(starter_fullstack_config: ProjectConfig) -> None:
    content = generate_backend_dockerfile(starter_fullstack_config)
    assert "COPY backend/ ." in content
    assert "gunicorn" in content
    assert "api.wsgi:application" in content
    assert "FROM" in content and "AS development" in content and "AS production" in content


def test_backend_dockerfile_fastapi() -> None:
    config = _config(BackendFramework.FASTAPI, FrontendFramework.REACT_VITE)
    content = generate_backend_dockerfile(config)
    assert "uvicorn" in content
    assert "app.main:app" in content
    assert "COPY backend/ ." in content


def test_backend_dockerfile_nestjs() -> None:
    config = _config(BackendFramework.NESTJS, FrontendFramework.REACT_VITE)
    content = generate_backend_dockerfile(config)
    assert "oven/bun" in content
    assert "bun run build" in content
    assert "start:dev" in content
    assert "COPY backend/" in content


def test_frontend_dockerfile_vite(starter_fullstack_config: ProjectConfig) -> None:
    content = generate_frontend_dockerfile(starter_fullstack_config)
    assert "COPY frontend/ ." in content
    assert "nginx" in content
    assert "docker/frontend/nginx.conf" in content


def test_frontend_dockerfile_nextjs() -> None:
    config = _config(BackendFramework.DJANGO_NINJA, FrontendFramework.NEXTJS)
    content = generate_frontend_dockerfile(config)
    assert "bun run build" in content
    assert '"bun", "run", "start"' in content
    assert "COPY frontend/" in content


def test_frontend_dev_dockerfile(starter_fullstack_config: ProjectConfig) -> None:
    content = generate_frontend_dev_dockerfile(starter_fullstack_config)
    assert '"bun", "run", "dev"' in content
    assert "COPY frontend/" in content


def test_frontend_nginx_conf() -> None:
    content = generate_frontend_nginx_conf()
    assert "try_files $uri $uri/ /index.html;" in content
    assert "listen 80" in content
