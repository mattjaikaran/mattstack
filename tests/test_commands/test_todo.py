"""Tests for mattstack todo (task SSOT)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from mattstack.commands.todo import (
    move_item,
    open_todo_items,
    parse_todo_items,
    read_open_tasks,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_todo_items() -> None:
    content = "- [x] done thing\n- [ ] open thing\n- not a task\n## heading\n"
    items = parse_todo_items(content)

    assert len(items) == 2
    assert items[0].text == "done thing" and items[0].checked is True
    assert items[1].text == "open thing" and items[1].checked is False


def test_open_todo_items() -> None:
    content = "- [x] done\n- [ ] a\n- [ ] b\n"
    assert open_todo_items(content) == ["a", "b"]


def test_read_open_tasks_missing_file(tmp_path: Path) -> None:
    assert read_open_tasks(tmp_path) == []


def test_read_open_tasks(tmp_path: Path) -> None:
    _write(tmp_path / "tasks" / "todo.md", "- [x] done\n- [ ] pending\n")
    assert read_open_tasks(tmp_path) == ["pending"]


def test_move_item(tmp_path: Path) -> None:
    todo = tmp_path / "tasks" / "todo.md"
    done = tmp_path / "tasks" / "completed.md"
    _write(todo, "- [x] fix login\n- [ ] other\n")

    text = move_item(todo, done, "fix login", date(2026, 8, 12), "abc1234")

    assert text == "fix login"
    remaining = todo.read_text(encoding="utf-8")
    assert "fix login" not in remaining
    assert "- [ ] other" in remaining
    assert "- fix login (2026-08-12 · abc1234)" in done.read_text(encoding="utf-8")


def test_move_item_not_found(tmp_path: Path) -> None:
    todo = tmp_path / "tasks" / "todo.md"
    done = tmp_path / "tasks" / "completed.md"
    _write(todo, "- [ ] other\n")

    with pytest.raises(ValueError, match="No todo item matches"):
        move_item(todo, done, "missing", date(2026, 8, 12), "abc1234")


def test_move_item_unchecked(tmp_path: Path) -> None:
    todo = tmp_path / "tasks" / "todo.md"
    done = tmp_path / "tasks" / "completed.md"
    _write(todo, "- [ ] open item\n")

    with pytest.raises(ValueError, match="not checked"):
        move_item(todo, done, "open item", date(2026, 8, 12), "abc1234")


def test_move_item_appends_to_existing_completed(tmp_path: Path) -> None:
    todo = tmp_path / "tasks" / "todo.md"
    done = tmp_path / "tasks" / "completed.md"
    _write(todo, "- [x] second\n")
    _write(done, "- first (2026-08-01 · deadbeef)\n")

    move_item(todo, done, "second", date(2026, 8, 12), "abc1234")

    completed = done.read_text(encoding="utf-8")
    assert completed.startswith("- first (2026-08-01 · deadbeef)")
    assert "- second (2026-08-12 · abc1234)" in completed
