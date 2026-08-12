"""mattstack.yml control-plane template for generated projects."""

from __future__ import annotations


def generate_mattstack_yml() -> str:
    """Generate a commented mattstack.yml template matching the schema defaults."""
    return """\
# mattstack.yml — control-plane configuration for mattstack-cli.
# Every key is optional; missing keys fall back to the defaults shown here.

version: 1          # Config schema version (do not change).

strict: true        # Enforce strict policy checks.
protect_main: false # Block direct commits to the main branch.
required_reviews: 1 # Approvals required before merging a PR.
coverage_floor: 80  # Minimum coverage percentage enforced in CI.
file_length: 400    # Maximum allowed lines per source file.

deps:
  mode: approval        # Dependency change policy: approval | allow | deny.
  manifest: DEPENDENCIES.md  # File listing approved dependencies.

scope:
  enforce: true     # Enforce scope boundaries between modules.

board:
  backend: none     # Task board backend (e.g. none, axis).
  url: ""           # Board base URL; empty when backend is none.
  api_key_env: AXIS_API_KEY  # Env var holding the board API key.
  project_slug: default      # Board project identifier.

notify:
  backend: none     # Notification backend (e.g. none, telegram).
  webhook_url_env: DEPLOY_WEBHOOK_URL  # Env var for the deploy webhook URL.
  chat_id_env: TELEGRAM_CHAT_ID        # Env var for the Telegram chat ID.
"""
