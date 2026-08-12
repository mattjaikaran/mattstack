"""Linear board backend — NOT IMPLEMENTED (stub).

One-way export adapter for Linear (GraphQL, LINEAR_API_KEY). Not yet built;
use ``board.backend: axis`` or ``none`` until it exists.
"""

from __future__ import annotations

from mattstack.boards.base import StubBoardBackend


class LinearBackend(StubBoardBackend):
    """Stub: every method raises NotImplementedError."""

    backend_name = "linear"
