"""Jira board backend — NOT IMPLEMENTED (stub).

One-way export adapter for Jira (REST v3, JIRA_API_TOKEN). Not yet built;
use ``board.backend: axis`` or ``none`` until it exists.
"""

from __future__ import annotations

from mattstack.boards.base import StubBoardBackend


class JiraBackend(StubBoardBackend):
    """Stub: every method raises NotImplementedError."""

    backend_name = "jira"
