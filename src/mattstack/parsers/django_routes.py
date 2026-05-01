"""Parse Django Ninja route decorators and controller registration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Route:
    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str
    function_name: str
    file: Path
    line: int
    has_auth: bool = False
    is_stub: bool = False


# Patterns for django-ninja decorators:
# @router.get("/path"), @api.post("/path"), @http_get("/path")
ROUTE_RE = re.compile(
    r"@(?:\w+)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"
    r"(?:.*?auth\s*=\s*(\w+))?"
    r"[^)]*\)",
    re.IGNORECASE | re.DOTALL,
)

# Alternative: @http_get, @http_post etc.
HTTP_DECORATOR_RE = re.compile(
    r"@http_(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"
    r"(?:.*?auth\s*=\s*(\w+))?"
    r"[^)]*\)",
    re.IGNORECASE | re.DOTALL,
)

# Function def following a route decorator
FUNC_DEF_RE = re.compile(r"^def\s+(\w+)\s*\(", re.MULTILINE)

# Router registration: router.add_router("/prefix", module.router)
ROUTER_REG_RE = re.compile(
    r"(?:api|router)\.add_router\s*\(\s*['\"]([^'\"]+)['\"]",
)

# Stub patterns: pass, ..., raise NotImplementedError
STUB_RE = re.compile(
    r"^\s+(pass|\.\.\.|raise NotImplementedError)\s*$",
    re.MULTILINE,
)


def parse_routes_file(path: Path) -> list[Route]:
    """Parse all route decorators from a Python file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    routes: list[Route] = []

    # Find all route decorators
    for pattern in (ROUTE_RE, HTTP_DECORATOR_RE):
        for match in pattern.finditer(text):
            method = match.group(1).upper()
            route_path = match.group(2)
            line_num = text[: match.start()].count("\n") + 1

            # Check for auth parameter
            has_auth = False
            if match.lastindex and match.lastindex >= 3 and match.group(3):
                has_auth = match.group(3).lower() not in ("none", "false")
            elif "auth=" in match.group(0):
                has_auth = True

            # Find the function name (next def after this decorator)
            func_name = "unknown"
            remaining = text[match.end() :]
            func_match = FUNC_DEF_RE.search(remaining)
            if func_match:
                func_name = func_match.group(1)

            # Check if function body is a stub
            is_stub = False
            if func_match:
                func_start = match.end() + func_match.end()
                # Look at next few lines for stub patterns
                func_line = text[:func_start].count("\n")
                body_lines = lines[func_line : func_line + 5]
                body_text = "\n".join(body_lines)
                is_stub = bool(STUB_RE.search(body_text))

            routes.append(
                Route(
                    method=method,
                    path=route_path,
                    function_name=func_name,
                    file=path,
                    line=line_num,
                    has_auth=has_auth,
                    is_stub=is_stub,
                )
            )

    return routes


def find_route_files(project_path: Path) -> list[Path]:
    """Find Python files likely containing route definitions."""
    from mattstack.parsers.utils import find_files

    patterns = [
        "**/api.py",
        "**/api/*.py",
        "**/routes.py",
        "**/routes/*.py",
        "**/controllers.py",
        "**/controllers/*.py",
        "**/endpoints.py",
        "**/endpoints/*.py",
        "**/views.py",
        "**/views/*.py",
    ]
    return find_files(project_path, patterns)


# ── ninja-extra @api_controller parsing ────────────────────────────────────


@dataclass
class ControllerEndpoint:
    method: str        # GET POST PUT DELETE PATCH
    path: str
    handler: str
    response: str | None
    auth: bool


@dataclass
class Controller:
    name: str
    prefix: str
    tag: str | None
    file: Path
    line: int
    endpoints: list[ControllerEndpoint] = field(default_factory=list)


# @api_controller("/products", tags=["Products"])
API_CONTROLLER_RE = re.compile(
    r"@api_controller\s*\(\s*['\"]([^'\"]*)['\"]"
    r"(?:[^)]*tags\s*=\s*\[.*?['\"]([^'\"]*)['\"])?",
    re.DOTALL,
)

# class ProductController(BaseController):
CONTROLLER_CLASS_RE = re.compile(r"^class\s+(\w+Controller)\s*\(", re.MULTILINE)

# @http_get("/", response=list[ProductSchema], auth=JWTAuth())
HTTP_METHOD_FULL_RE = re.compile(
    r"@http_(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]*)['\"]"
    r"(?:[^)]*response\s*=\s*([^,)]+))?"
    r"(?:[^)]*auth\s*=\s*(\w+))?"
    r"[^)]*\)",
    re.IGNORECASE | re.DOTALL,
)


def parse_controller_file(path: Path) -> list[Controller]:
    """Parse @api_controller classes and their @http_* endpoints from a file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    controllers: list[Controller] = []

    # Find each @api_controller decorator
    for dec_match in API_CONTROLLER_RE.finditer(text):
        prefix = dec_match.group(1)
        tag = dec_match.group(2) if dec_match.lastindex and dec_match.lastindex >= 2 else None

        # Find the class definition after this decorator
        class_match = CONTROLLER_CLASS_RE.search(text, dec_match.end())
        if not class_match:
            continue

        class_name = class_match.group(1)
        class_line = text[: class_match.start()].count("\n") + 1

        # Determine class body end (next top-level class or EOF)
        next_class = CONTROLLER_CLASS_RE.search(text, class_match.end())
        body_end = next_class.start() if next_class else len(text)
        class_body = text[class_match.end():body_end]

        endpoints: list[ControllerEndpoint] = []
        for ep_match in HTTP_METHOD_FULL_RE.finditer(class_body):
            method = ep_match.group(1).upper()
            ep_path = ep_match.group(2)
            response_raw = ep_match.group(3).strip() if ep_match.group(3) else None
            auth_val = ep_match.group(4) if ep_match.lastindex and ep_match.lastindex >= 4 else None
            has_auth = bool(auth_val and auth_val.lower() not in ("none", "false"))

            # Find handler name (next def after this decorator — may be indented)
            remaining = class_body[ep_match.end():]
            _indented_def_re = re.compile(r"def\s+(\w+)\s*\(")
            handler_match = _indented_def_re.search(remaining)
            handler = handler_match.group(1) if handler_match else "unknown"

            endpoints.append(
                ControllerEndpoint(
                    method=method,
                    path=ep_path,
                    handler=handler,
                    response=response_raw,
                    auth=has_auth,
                )
            )

        controllers.append(
            Controller(
                name=class_name,
                prefix=prefix,
                tag=tag,
                file=path,
                line=class_line,
                endpoints=endpoints,
            )
        )

    return controllers


def find_controller_files(project_path: Path) -> list[Path]:
    """Find Python files likely containing @api_controller classes."""
    from mattstack.parsers.utils import find_files

    patterns = [
        "**/controllers/*.py",
        "**/controllers.py",
    ]
    return find_files(project_path, patterns)
