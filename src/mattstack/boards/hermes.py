"""Hermes board backend — NOT IMPLEMENTED (stub).

Hermes' kanban is unresolved (design doc open question 1). Not yet built;
use ``board.backend: axis`` or ``none`` until it exists.
"""

from __future__ import annotations

from mattstack.boards.base import StubBoardBackend


class HermesBackend(StubBoardBackend):
    """Stub: every method raises NotImplementedError."""

    backend_name = "hermes"
