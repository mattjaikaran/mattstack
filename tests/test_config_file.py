"""Tests for mattstack.yml control-plane configuration."""

from __future__ import annotations

from pathlib import Path

from mattstack.config_file import load_config


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "mattstack.yml")

    assert config.version == 1
    assert config.strict is True
    assert config.protect_main is False
    assert config.required_reviews == 1
    assert config.coverage_floor == 80
    assert config.file_length == 400

    assert config.deps.mode == "approval"
    assert config.deps.manifest == "DEPENDENCIES.md"

    assert config.scope.enforce is True

    assert config.board.backend == "none"
    assert config.board.url == ""
    assert config.board.api_key_env == "AXIS_API_KEY"
    assert config.board.project_slug == "default"

    assert config.notify.backend == "none"
    assert config.notify.webhook_url_env == "DEPLOY_WEBHOOK_URL"
    assert config.notify.chat_id_env == "TELEGRAM_CHAT_ID"


def test_partial_yaml_overrides_with_defaults_for_rest(tmp_path: Path) -> None:
    f = tmp_path / "mattstack.yml"
    f.write_text("strict: false\nboard:\n  backend: axis\n")

    config = load_config(f)

    # Overridden keys.
    assert config.strict is False
    assert config.board.backend == "axis"

    # Everything else falls back to defaults.
    assert config.version == 1
    assert config.protect_main is False
    assert config.required_reviews == 1
    assert config.coverage_floor == 80
    assert config.file_length == 400
    assert config.deps.mode == "approval"
    assert config.deps.manifest == "DEPENDENCIES.md"
    assert config.scope.enforce is True
    assert config.board.url == ""
    assert config.board.api_key_env == "AXIS_API_KEY"
    assert config.board.project_slug == "default"
    assert config.notify.backend == "none"
    assert config.notify.webhook_url_env == "DEPLOY_WEBHOOK_URL"
    assert config.notify.chat_id_env == "TELEGRAM_CHAT_ID"


def test_full_yaml_round_trip(tmp_path: Path) -> None:
    f = tmp_path / "mattstack.yml"
    f.write_text(
        "\n".join(
            [
                "version: 2",
                "strict: false",
                "protect_main: true",
                "required_reviews: 3",
                "coverage_floor: 90",
                "file_length: 500",
                "deps:",
                "  mode: deny",
                "  manifest: DEPS.md",
                "scope:",
                "  enforce: false",
                "board:",
                "  backend: axis",
                "  url: https://axis.example.com",
                "  api_key_env: MY_AXIS_KEY",
                "  project_slug: my-slug",
                "notify:",
                "  backend: telegram",
                "  webhook_url_env: MY_WEBHOOK",
                "  chat_id_env: MY_CHAT",
            ]
        )
        + "\n"
    )

    config = load_config(f)

    assert config.version == 2
    assert config.strict is False
    assert config.protect_main is True
    assert config.required_reviews == 3
    assert config.coverage_floor == 90
    assert config.file_length == 500

    assert config.deps.mode == "deny"
    assert config.deps.manifest == "DEPS.md"

    assert config.scope.enforce is False

    assert config.board.backend == "axis"
    assert config.board.url == "https://axis.example.com"
    assert config.board.api_key_env == "MY_AXIS_KEY"
    assert config.board.project_slug == "my-slug"

    assert config.notify.backend == "telegram"
    assert config.notify.webhook_url_env == "MY_WEBHOOK"
    assert config.notify.chat_id_env == "MY_CHAT"
