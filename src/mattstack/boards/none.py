"""Null board backend (no-op for board.backend: none)."""

from __future__ import annotations

from typing import Any

from mattstack.boards.base import BoardBackend


class NullBackend(BoardBackend):
    """No-op backend; every method returns an empty, successful result."""

    def create_task(self, title: str, project: str | None = None, **fields: Any) -> dict[str, Any]:
        return {}

    def list_tasks(self, **filters: Any) -> list[dict[str, Any]]:
        return []

    def update_task(self, task_id: str, **updates: Any) -> dict[str, Any]:
        return {}

    def transition_task(
        self, task_id: str, target_status: str, comment: str = ""
    ) -> dict[str, Any]:
        return {}

    def claim_task(self, task_id: str, agent_name: str) -> dict[str, Any]:
        return {}

    def get_next_task(self, agent_name: str, project: str | None = None) -> dict[str, Any]:
        return {}

    def link_pr(self, task_id: str, pr_url: str, pr_number: int | None = None) -> dict[str, Any]:
        return {}
