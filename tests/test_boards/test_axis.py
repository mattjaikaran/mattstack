"""Tests for the pluggable board backends (design doc §2)."""

from __future__ import annotations

import json

import httpx
import pytest

from mattstack.boards import get_board_backend
from mattstack.boards.axis import AxisBackend
from mattstack.boards.hermes import HermesBackend
from mattstack.boards.jira import JiraBackend
from mattstack.boards.linear import LinearBackend
from mattstack.boards.none import NullBackend
from mattstack.config_file import BoardConfig


def _backend() -> tuple[AxisBackend, list[httpx.Request]]:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = AxisBackend(
        base_url="https://axis.example.com/api/v1",
        api_key="secret",
        project_slug="default",
        client=client,
    )
    return backend, calls


def test_create_task_posts_batch() -> None:
    backend, calls = _backend()

    backend.create_task("Fix login", project="web", priority="high")

    req = calls[0]
    assert req.method == "POST"
    assert str(req.url) == "https://axis.example.com/api/v1/tasks/batch"
    assert req.headers["Authorization"] == "Bearer secret"
    body = json.loads(req.content)
    assert body["tasks"][0]["title"] == "Fix login"
    assert body["tasks"][0]["project"] == "web"
    assert body["tasks"][0]["priority"] == "high"


def test_create_task_defaults_project_slug() -> None:
    backend, calls = _backend()

    backend.create_task("Fix login")

    body = json.loads(calls[0].content)
    assert body["tasks"][0]["project"] == "default"


def test_list_tasks_posts_search() -> None:
    backend, calls = _backend()

    backend.list_tasks(status="todo")

    req = calls[0]
    assert req.method == "POST"
    assert str(req.url).endswith("/tasks/search")
    assert json.loads(req.content) == {"status": "todo"}


def test_update_task_patches_bulk_update() -> None:
    backend, calls = _backend()

    backend.update_task("t1", status="done")

    req = calls[0]
    assert req.method == "PATCH"
    assert str(req.url).endswith("/tasks/bulk-update")
    body = json.loads(req.content)
    assert body["tasks"][0]["id"] == "t1"
    assert body["tasks"][0]["status"] == "done"


def test_transition_task_posts_transition() -> None:
    backend, calls = _backend()

    backend.transition_task("t1", "in_progress", comment="starting")

    req = calls[0]
    assert req.method == "POST"
    assert str(req.url).endswith("/tasks/t1/transition")
    assert json.loads(req.content) == {"status": "in_progress", "comment": "starting"}


def test_claim_task_posts_claim() -> None:
    backend, calls = _backend()

    backend.claim_task("t1", "agent-7")

    req = calls[0]
    assert req.method == "POST"
    assert str(req.url).endswith("/tasks/t1/claim")
    assert json.loads(req.content) == {"agent": "agent-7"}


def test_get_next_task_posts_next() -> None:
    backend, calls = _backend()

    backend.get_next_task("agent-7", project="web")

    req = calls[0]
    assert req.method == "POST"
    assert str(req.url).endswith("/tasks/next")
    assert json.loads(req.content) == {"agent": "agent-7", "project": "web"}


def test_link_pr_posts_link_pr() -> None:
    backend, calls = _backend()

    backend.link_pr("t1", "https://github.com/a/b/pull/3", pr_number=3)

    req = calls[0]
    assert req.method == "POST"
    assert str(req.url).endswith("/tasks/t1/link-pr")
    assert json.loads(req.content) == {
        "pr_url": "https://github.com/a/b/pull/3",
        "pr_number": 3,
    }


def test_null_backend_is_noop() -> None:
    backend = NullBackend()

    assert backend.create_task("x") == {}
    assert backend.list_tasks() == []
    assert backend.update_task("t") == {}
    assert backend.transition_task("t", "done") == {}
    assert backend.claim_task("t", "a") == {}
    assert backend.get_next_task("a") == {}
    assert backend.link_pr("t", "url") == {}


def test_stub_backends_raise_not_implemented() -> None:
    for cls in (LinearBackend, JiraBackend, HermesBackend):
        backend = cls()
        with pytest.raises(NotImplementedError):
            backend.create_task("x")


def test_factory_resolves_backends() -> None:
    assert isinstance(get_board_backend(BoardConfig(backend="none")), NullBackend)
    assert isinstance(get_board_backend(BoardConfig(backend="axis")), AxisBackend)
    assert isinstance(get_board_backend(BoardConfig(backend="linear")), LinearBackend)
    assert isinstance(get_board_backend(BoardConfig(backend="jira")), JiraBackend)
    assert isinstance(get_board_backend(BoardConfig(backend="hermes")), HermesBackend)


def test_factory_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unknown board backend"):
        get_board_backend(BoardConfig(backend="bogus"))


def test_sync_open_tasks_pushes_to_backend(tmp_path) -> None:
    from mattstack.commands.board import sync_open_tasks

    (tmp_path / "tasks").mkdir(parents=True)
    (tmp_path / "tasks" / "todo.md").write_text(
        "- [x] done\n- [ ] one\n- [ ] two\n", encoding="utf-8"
    )

    created: list[str] = []

    class FakeBackend:
        def create_task(self, title: str, project: str | None = None, **fields) -> dict:
            created.append(title)
            return {}

    count = sync_open_tasks(FakeBackend(), tmp_path, "proj")

    assert count == 2
    assert created == ["one", "two"]
