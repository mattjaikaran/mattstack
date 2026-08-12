"""Notify command: send a deploy-complete notification."""

from __future__ import annotations

from pathlib import Path

import httpx
import typer

from mattstack.config_file import load_config
from mattstack.notify import DeployEnvelope, send_deploy_notification
from mattstack.utils.console import print_error, print_success


def run_notify(
    path: Path,
    app: str = "",
    commit: str = "",
    env: str = "production",
    frontend_url: str = "",
    backend_url: str = "",
) -> None:
    """Build the deploy envelope and send it via the configured backend."""
    config = load_config(path / "mattstack.yml")
    envelope = DeployEnvelope(
        app=app,
        commit=commit,
        env=env,
        frontend_url=frontend_url,
        backend_url=backend_url,
    )
    try:
        send_deploy_notification(config, envelope)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from None
    except httpx.HTTPError as e:
        print_error(f"Notification failed: {e}")
        raise typer.Exit(code=1) from None
    print_success("Deploy notification sent")
