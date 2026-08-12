"""Tests for consolidated docker-compose templates."""

from __future__ import annotations

from mattstack.config import ProjectConfig
from mattstack.templates.docker_compose import generate_docker_compose
from mattstack.templates.docker_compose_prod import generate_docker_compose_prod


def test_dev_compose_uses_relocated_dockerfiles(starter_fullstack_config: ProjectConfig) -> None:
    content = generate_docker_compose(starter_fullstack_config)
    assert "context: ." in content
    assert "dockerfile: docker/backend/Dockerfile" in content
    assert "dockerfile: docker/frontend/Dockerfile.dev" in content
    assert "target: development" in content


def test_dev_compose_has_celery_profile(starter_fullstack_config: ProjectConfig) -> None:
    content = generate_docker_compose(starter_fullstack_config)
    assert "profiles:" in content
    assert "- celery" in content


def test_prod_compose_uses_relocated_dockerfiles(starter_fullstack_config: ProjectConfig) -> None:
    content = generate_docker_compose_prod(starter_fullstack_config)
    assert "context: ." in content
    assert "dockerfile: docker/backend/Dockerfile" in content
    assert "dockerfile: docker/frontend/Dockerfile" in content
