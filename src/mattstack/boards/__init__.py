"""Board backend factory: resolve ``board.backend`` to a BoardBackend."""

from __future__ import annotations

import os

from mattstack.boards.axis import AxisBackend
from mattstack.boards.base import BoardBackend
from mattstack.boards.hermes import HermesBackend
from mattstack.boards.jira import JiraBackend
from mattstack.boards.linear import LinearBackend
from mattstack.boards.none import NullBackend
from mattstack.config_file import BoardConfig


def get_board_backend(config: BoardConfig) -> BoardBackend:
    """Build the configured board backend from a :class:`BoardConfig`."""
    backend = (config.backend or "none").strip().lower()

    if backend == "axis":
        api_key = os.environ.get(config.api_key_env or "AXIS_API_KEY", "")
        return AxisBackend(
            base_url=config.url or "",
            api_key=api_key,
            project_slug=config.project_slug or "default",
        )

    if backend == "none":
        return NullBackend()

    if backend == "hermes":
        return HermesBackend()
    if backend == "linear":
        return LinearBackend()
    if backend == "jira":
        return JiraBackend()

    raise ValueError(f"Unknown board backend: {config.backend!r}")
