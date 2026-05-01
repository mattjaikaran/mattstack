"""Generate command: scaffold individual components for Django + React projects."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Annotated

import typer

from mattstack.utils.console import console, print_error, print_info, print_success, print_warning

generate_app = typer.Typer(
    name="generate",
    help="Scaffold models, endpoints, components, pages, hooks, and schemas.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# ---------------------------------------------------------------------------
# Field type mappings
# ---------------------------------------------------------------------------

DJANGO_FIELD_MAP: dict[str, str] = {
    "str": "CharField(max_length=255)",
    "int": "IntegerField()",
    "float": "FloatField()",
    "decimal": "DecimalField(max_digits=10, decimal_places=2)",
    "bool": "BooleanField(default=False)",
    "text": "TextField()",
    "date": "DateField()",
    "datetime": "DateTimeField()",
    "email": "EmailField()",
    "url": "URLField()",
    "uuid": "UUIDField(default=uuid.uuid4, editable=False)",
}

PYDANTIC_TYPE_MAP: dict[str, str] = {
    "str": "str",
    "int": "int",
    "float": "float",
    "decimal": "Decimal",
    "bool": "bool",
    "text": "str",
    "date": "date",
    "datetime": "datetime",
    "email": "EmailStr",
    "url": "HttpUrl",
    "uuid": "UUID",
}

TS_TYPE_MAP: dict[str, str] = {
    "str": "string",
    "int": "number",
    "float": "number",
    "decimal": "number",
    "bool": "boolean",
    "text": "string",
    "date": "string",
    "datetime": "string",
    "email": "string",
    "url": "string",
    "uuid": "string",
}

# ---------------------------------------------------------------------------
# Field parsing
# ---------------------------------------------------------------------------


def _parse_fields(raw: list[str]) -> list[tuple[str, str, str | None]]:
    """Parse field specs like 'title:str' or 'category:fk:Category'.

    Returns list of (field_name, field_type, fk_target | None).
    """
    fields: list[tuple[str, str, str | None]] = []
    for spec in raw:
        parts = spec.split(":")
        if len(parts) == 3 and parts[1] == "fk":
            fields.append((parts[0], "fk", parts[2]))
        elif len(parts) == 2:
            if parts[1] not in DJANGO_FIELD_MAP and parts[1] != "fk":
                print_error(
                    f"Unknown field type '{parts[1]}'. "
                    f"Valid: {', '.join(sorted(DJANGO_FIELD_MAP))} or fk:ModelName"
                )
                raise typer.Exit(code=1)
            fields.append((parts[0], parts[1], None))
        else:
            print_error(f"Invalid field spec '{spec}'. Use name:type or name:fk:ModelName")
            raise typer.Exit(code=1)
    return fields


# ---------------------------------------------------------------------------
# Project structure detection
# ---------------------------------------------------------------------------


def _find_project_root(start: Path) -> Path:
    """Walk up to find a directory containing backend/ or frontend/."""
    current = start.resolve()
    for _ in range(10):
        if (current / "backend").is_dir() or (current / "frontend").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return start.resolve()


def _detect_django_app(project_root: Path, app_override: str | None) -> str:
    """Detect or validate the Django app name."""
    if app_override:
        return app_override

    apps_dir = project_root / "backend" / "apps"
    if apps_dir.is_dir():
        candidates = [
            d.name
            for d in apps_dir.iterdir()
            if d.is_dir() and not d.name.startswith("__")
        ]
        if len(candidates) == 1:
            return candidates[0]
        if "core" in candidates:
            return "core"
        if candidates:
            return candidates[0]

    return "core"


def _detect_frontend_framework(project_root: Path) -> str:
    """Detect frontend framework: tanstack, nextjs, vite, or rsbuild."""
    frontend = project_root / "frontend"
    if not frontend.is_dir():
        return "unknown"

    pkg_json = frontend / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:
                return "nextjs"
            if "@tanstack/react-router" in deps:
                return "tanstack"
        except (json.JSONDecodeError, OSError):
            pass

    if (frontend / "next.config.ts").exists() or (frontend / "next.config.js").exists():
        return "nextjs"
    if (frontend / "rsbuild.config.ts").exists() or (frontend / "rsbuild.config.js").exists():
        return "rsbuild"
    if (frontend / "vite.config.ts").exists() or (frontend / "vite.config.js").exists():
        return "vite"

    return "unknown"


def _to_snake(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()


def _to_pascal(name: str) -> str:
    """Convert snake_case or kebab-case to PascalCase."""
    return "".join(word.capitalize() for word in re.split(r"[_\-]", name))


def _to_camel(name: str) -> str:
    """Convert to camelCase."""
    pascal = _to_pascal(name)
    return pascal[0].lower() + pascal[1:] if pascal else ""


def _ensure_dir(path: Path, *, dry_run: bool) -> None:
    """Create directory and __init__.py if needed."""
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def _write_file(path: Path, content: str, *, dry_run: bool) -> None:
    """Write file, creating parent dirs. Prints path in dry-run mode."""
    if dry_run:
        console.print(f"  [dim]Would create:[/dim] {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _ensure_init(directory: Path, *, dry_run: bool) -> None:
    """Ensure __init__.py exists in a Python package directory."""
    init = directory / "__init__.py"
    if not init.exists() and not dry_run:
        init.parent.mkdir(parents=True, exist_ok=True)
        init.write_text("")


# ---------------------------------------------------------------------------
# Auto-wiring helpers
# ---------------------------------------------------------------------------


def _update_init_import(init_file: Path, import_line: str, *, dry_run: bool) -> bool:
    """Append an import line to __init__.py if not already present. Returns True if added."""
    if dry_run:
        console.print(f"  [dim]Would update:[/dim] {init_file}")
        return True

    init_file.parent.mkdir(parents=True, exist_ok=True)
    existing = init_file.read_text() if init_file.exists() else ""
    if import_line in existing:
        return False
    if existing and not existing.endswith("\n"):
        existing += "\n"
    init_file.write_text(existing + import_line + "\n")
    return True


def _generate_admin_file(pascal: str, snake: str, app_name: str, fields: list[tuple[str, str, str | None]]) -> str:
    """Generate a per-model unfold admin file."""
    str_fields = [fname for fname, ftype, _ in fields if ftype in ("str", "text", "email")]
    list_display_fields = str_fields[:3] if str_fields else []
    list_display = '["id"' + "".join(f', "{f}"' for f in list_display_fields) + ', "created_at"]'

    return f'''"""Admin configuration for {pascal}."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.{app_name}.models.{snake} import {pascal}


@admin.register({pascal})
class {pascal}Admin(ModelAdmin):
    list_display = {list_display}
    list_filter = ("created_at",)
    search_fields = {tuple(list_display_fields) if list_display_fields else ('("id",)'[:-2] + '"id")')!r}
    readonly_fields = ("id", "created_at", "updated_at")
'''


def _build_admin_file(pascal: str, snake: str, app_name: str, fields: list[tuple[str, str, str | None]]) -> str:
    """Build per-model unfold admin file content."""
    str_fields = [fname for fname, ftype, _ in fields if ftype in ("str", "text", "email")]
    display_fields = str_fields[:3]
    list_display_items = ["id"] + display_fields + ["created_at"]
    list_display = "[" + ", ".join(f'"{f}"' for f in list_display_items) + "]"
    search_fields: list[str] = display_fields if display_fields else ["id"]
    search_tuple = "(" + ", ".join(f'"{f}"' for f in search_fields) + ("," if len(search_fields) == 1 else "") + ")"

    return (
        f'"""Admin configuration for {pascal}."""\n'
        "\n"
        "from django.contrib import admin\n"
        "from unfold.admin import ModelAdmin\n"
        "\n"
        f"from apps.{app_name}.models.{snake} import {pascal}\n"
        "\n"
        "\n"
        f"@admin.register({pascal})\n"
        f"class {pascal}Admin(ModelAdmin):\n"
        f"    list_display = {list_display}\n"
        f'    list_filter = ("created_at",)\n'
        f"    search_fields = {search_tuple}\n"
        f'    readonly_fields = ("id", "created_at", "updated_at")\n'
    )


# ---------------------------------------------------------------------------
# Code generators
# ---------------------------------------------------------------------------


def _generate_django_model(
    name: str,
    fields: list[tuple[str, str, str | None]],
) -> str:
    """Generate Django model source code using AbstractBaseModel."""
    pascal = _to_pascal(name)
    needs_uuid = any(ft == "uuid" for _, ft, _ in fields)

    fk_models: list[str] = []
    for _, ft, fk_target in fields:
        if ft == "fk" and fk_target:
            fk_models.append(fk_target)

    lines = [
        f'"""Django model for {pascal}."""',
        "",
        "from __future__ import annotations",
        "",
    ]
    if needs_uuid:
        lines.append("import uuid")
        lines.append("")
    lines.append("from django.db import models")
    lines.append("from core.models.base import AbstractBaseModel")

    if fk_models:
        lines.append("")
        for fk in fk_models:
            snake_fk = _to_snake(fk)
            lines.append(f"from .{snake_fk} import {fk}")

    lines.extend([
        "",
        "",
        f"class {pascal}(AbstractBaseModel):",
    ])

    if not fields:
        lines.append("    pass")
    else:
        for fname, ftype, fk_target in fields:
            if ftype == "fk" and fk_target:
                lines.append(
                    f"    {fname} = models.ForeignKey("
                    f"{fk_target}, on_delete=models.CASCADE, related_name=\"{_to_snake(pascal)}s\")"
                )
            else:
                django_field = DJANGO_FIELD_MAP[ftype]
                lines.append(f"    {fname} = models.{django_field}")

    lines.extend([
        "",
        "    class Meta:",
        f'        verbose_name = "{pascal}"',
        f'        verbose_name_plural = "{pascal}s"',
        f'        ordering = ["-created_at"]',
        "",
        "    def __str__(self) -> str:",
    ])

    str_field = "pk"
    for fname, ftype, _ in fields:
        if ftype in ("str", "text", "email"):
            str_field = fname
            break

    if str_field == "pk":
        lines.append(f'        return f"{pascal}({{self.pk}})"')
    else:
        lines.append(f"        return self.{str_field}")

    lines.append("")
    return "\n".join(lines)


def _generate_pydantic_schema(
    name: str,
    fields: list[tuple[str, str, str | None]],
) -> str:
    """Generate ninja Schema source code following BaseSchema/Create/Update/Response pattern."""
    pascal = _to_pascal(name)
    type_imports: set[str] = set()
    ninja_imports: set[str] = {"Schema"}

    for _, ftype, _ in fields:
        if ftype in ("fk", "uuid"):
            type_imports.add("UUID")
        elif ftype == "date":
            type_imports.add("date")
        elif ftype == "datetime":
            type_imports.add("datetime")
        elif ftype == "decimal":
            type_imports.add("Decimal")
        elif ftype == "email":
            ninja_imports.add("EmailStr")
        elif ftype == "url":
            ninja_imports.add("HttpUrl")

    lines = [
        f'"""Ninja schemas for {pascal}."""',
        "",
        "from __future__ import annotations",
        "",
    ]

    stdlib_imports: list[str] = []
    if "Decimal" in type_imports:
        stdlib_imports.append("from decimal import Decimal")
    datetime_types = sorted(type_imports & {"date", "datetime"})
    if datetime_types:
        stdlib_imports.append(f"from datetime import {', '.join(datetime_types)}")
    if "UUID" not in type_imports:
        # ResponseSchema always needs UUID and datetime
        pass
    stdlib_imports.append("from datetime import datetime")
    stdlib_imports.append("from uuid import UUID")

    # Deduplicate and sort
    seen: set[str] = set()
    deduped: list[str] = []
    for imp in stdlib_imports:
        if imp not in seen:
            seen.add(imp)
            deduped.append(imp)
    if deduped:
        lines.extend(sorted(deduped))
        lines.append("")

    lines.append("from ninja import Schema")
    lines.append("from pydantic import ConfigDict")
    if ninja_imports - {"Schema"}:
        lines[-1] = "from ninja import " + ", ".join(sorted(ninja_imports))
        lines.append("from pydantic import ConfigDict")
    lines.append("")

    def _field_lines(optional: bool = False) -> list[str]:
        result = []
        if not fields:
            result.append("    pass")
        else:
            for fname, ftype, _ in fields:
                py_type = "UUID" if ftype == "fk" else PYDANTIC_TYPE_MAP[ftype]
                if optional:
                    result.append(f"    {fname}: {py_type} | None = None")
                else:
                    result.append(f"    {fname}: {py_type}")
        return result

    # BaseSchema
    lines.extend([
        "",
        f"class {pascal}BaseSchema(Schema):",
    ])
    lines.extend(_field_lines())

    # CreateSchema
    lines.extend([
        "",
        "",
        f"class {pascal}CreateSchema({pascal}BaseSchema):",
        "    pass",
    ])

    # UpdateSchema
    lines.extend([
        "",
        "",
        f"class {pascal}UpdateSchema({pascal}BaseSchema):",
    ])
    if not fields:
        lines.append("    pass")
    else:
        for fname, ftype, _ in fields:
            py_type = "UUID" if ftype == "fk" else PYDANTIC_TYPE_MAP[ftype]
            lines.append(f"    {fname}: {py_type} | None = None")

    # ResponseSchema
    lines.extend([
        "",
        "",
        f"class {pascal}ResponseSchema({pascal}BaseSchema):",
        "    id: UUID",
        "    created_at: datetime",
        "    updated_at: datetime",
        "    model_config = ConfigDict(from_attributes=True)",
    ])

    lines.append("")
    return "\n".join(lines)


def _generate_api_controller(
    name: str,
    fields: list[tuple[str, str, str | None]],
    app_name: str,
) -> str:
    """Generate ninja-extra class-based controller with CRUD endpoints."""
    pascal = _to_pascal(name)
    snake = _to_snake(name)

    lines = [
        f'"""API controller for {pascal}."""',
        "",
        "from __future__ import annotations",
        "",
        "from uuid import UUID",
        "",
        "from django.shortcuts import get_object_or_404",
        "from ninja_extra import api_controller, http_delete, http_get, http_post, http_put",
        "",
        f"from apps.{app_name}.models.{snake} import {pascal}",
        f"from apps.{app_name}.schemas.{snake} import (",
        f"    {pascal}CreateSchema,",
        f"    {pascal}ResponseSchema,",
        f"    {pascal}UpdateSchema,",
        ")",
        "from core.auth import JWTAuth, OptionalJWTAuth",
        "from core.controllers.base_controller import BaseController, handle_exceptions",
        "",
        "",
        f'@api_controller("/{snake}s", tags=["{pascal}"])',
        f"class {pascal}Controller(BaseController):",
        f'    @http_get("/", response=list[{pascal}ResponseSchema])',
        "    @handle_exceptions()",
        f"    def list_{snake}s(self, request, search: str | None = None, limit: int = 20, offset: int = 0):",
        f'        """List {pascal}s with pagination."""',
        f"        qs = {pascal}.objects.all()",
        "        if search:",
        f"            qs = qs.filter(id__icontains=search)",
        "        return qs[offset:offset + limit]",
        "",
        f'    @http_get("/{{{snake}_id}}", response={{200: {pascal}ResponseSchema, 404: dict}}, auth=OptionalJWTAuth())',
        "    @handle_exceptions()",
        f"    def get_{snake}(self, request, {snake}_id: UUID):",
        f'        """Get a single {pascal}."""',
        f"        return get_object_or_404({pascal}, id={snake}_id)",
        "",
        f'    @http_post("/", response={{201: {pascal}ResponseSchema, 400: dict}}, auth=JWTAuth())',
        "    @handle_exceptions(success_status=201)",
        f"    def create_{snake}(self, request, payload: {pascal}CreateSchema):",
        f'        """Create a new {pascal}."""',
        f"        obj = {pascal}.objects.create(**payload.model_dump())",
        "        return obj",
        "",
        f'    @http_put("/{{{snake}_id}}", response={{200: {pascal}ResponseSchema, 403: dict}}, auth=JWTAuth())',
        "    @handle_exceptions()",
        f"    def update_{snake}(self, request, {snake}_id: UUID, payload: {pascal}UpdateSchema):",
        f'        """Update a {pascal}."""',
        f"        obj = get_object_or_404({pascal}, id={snake}_id)",
        "        for attr, value in payload.model_dump(exclude_unset=True).items():",
        "            setattr(obj, attr, value)",
        "        obj.save()",
        "        return obj",
        "",
        f'    @http_delete("/{{{snake}_id}}", response={{204: None}}, auth=JWTAuth())',
        "    @handle_exceptions()",
        f"    def delete_{snake}(self, request, {snake}_id: UUID):",
        f'        """Delete a {pascal}."""',
        f"        obj = get_object_or_404({pascal}, id={snake}_id)",
        "        obj.delete()",
        "        return 204, None",
        "",
    ]
    return "\n".join(lines)


# Keep old name as alias so existing callers don't break
_generate_api_router = _generate_api_controller


def _generate_endpoint_method(
    path: str,
    method: str,
    auth: bool,
) -> str:
    """Generate a single ninja-extra controller method."""
    method_lower = method.lower()
    func_name = re.sub(r"[{}/<>]", "", path).strip("/").replace("/", "_").replace("-", "_")
    if not func_name:
        func_name = "root"

    auth_param = f", auth=JWTAuth()" if auth else ""
    decorator = f'    @http_{method_lower}("{path}"{auth_param})'

    return "\n".join([
        decorator,
        "    @handle_exceptions()",
        f"    def {func_name}(self, request):",
        f'        """Handle {method} {path}."""',
        '        return {"message": "Not implemented"}',
        "",
    ])


def _generate_controller_file(segment: str, endpoint_method: str, auth: bool) -> str:
    """Generate a full controller file wrapping a single method."""
    pascal = _to_pascal(segment)
    auth_import = "\nfrom core.auth import JWTAuth" if auth else ""

    header = (
        '"""API controller."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from ninja_extra import api_controller, http_delete, http_get, http_post, http_put\n"
        f"{auth_import}\n"
        "from core.controllers.base_controller import BaseController, handle_exceptions\n"
        "\n"
        "\n"
        f'@api_controller("/{segment}s", tags=["{pascal}"])\n'
        f"class {pascal}Controller(BaseController):\n"
    )
    # Indent the method body (already indented by _generate_endpoint_method)
    return header + endpoint_method + "\n"


def _generate_react_component(name: str) -> str:
    """Generate a React TypeScript component."""
    lines = [
        f"interface {name}Props {{",
        "  className?: string;",
        "}",
        "",
        f"export function {name}({{ className }}: {name}Props) {{",
        "  return (",
        f'    <div className={{className}}>',
        f"      <h2>{name}</h2>",
        "    </div>",
        "  );",
        "}",
        "",
        f"export default {name};",
        "",
    ]
    return "\n".join(lines)


def _generate_react_test(name: str) -> str:
    """Generate a Vitest test for a React component."""
    lines = [
        'import { render, screen } from "@testing-library/react";',
        'import { describe, expect, it } from "vitest";',
        "",
        f'import {{ {name} }} from "./index";',
        "",
        f'describe("{name}", () => {{',
        f'  it("renders without crashing", () => {{',
        f"    render(<{name} />);",
        f'    expect(screen.getByText("{name}")).toBeDefined();',
        "  });",
        "});",
        "",
    ]
    return "\n".join(lines)


def _generate_tanstack_page(name: str) -> str:
    """Generate a TanStack Router page."""
    snake = _to_snake(name)
    pascal = _to_pascal(name)
    lines = [
        f'import {{ createFileRoute }} from "@tanstack/react-router";',
        "",
        f'export const Route = createFileRoute("/{snake}")({{',
        f"  component: {pascal}Page,",
        "});",
        "",
        f"function {pascal}Page() {{",
        "  return (",
        f'    <div className="container mx-auto p-4">',
        f"      <h1>{pascal}</h1>",
        "    </div>",
        "  );",
        "}",
        "",
    ]
    return "\n".join(lines)


def _generate_nextjs_page(name: str) -> str:
    """Generate a Next.js app router page."""
    pascal = _to_pascal(name)
    lines = [
        f"export default function {pascal}Page() {{",
        "  return (",
        f'    <div className="container mx-auto p-4">',
        f"      <h1>{pascal}</h1>",
        "    </div>",
        "  );",
        "}",
        "",
    ]
    return "\n".join(lines)


def _generate_hook(name: str) -> str:
    """Generate a React custom hook."""
    if not name.startswith("use"):
        name = f"use{_to_pascal(name)}"

    lines = [
        'import { useCallback, useState } from "react";',
        "",
        f"export function {name}() {{",
        "  const [data, setData] = useState<unknown>(null);",
        "  const [loading, setLoading] = useState(false);",
        "  const [error, setError] = useState<Error | null>(null);",
        "",
        "  const execute = useCallback(async () => {",
        "    setLoading(true);",
        "    setError(null);",
        "    try {",
        '      // TODO: implement',
        "      setData(null);",
        "    } catch (err) {",
        "      setError(err instanceof Error ? err : new Error(String(err)));",
        "    } finally {",
        "      setLoading(false);",
        "    }",
        "  }, []);",
        "",
        "  return { data, loading, error, execute };",
        "}",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


@generate_app.command("model")
def model(
    name: Annotated[str, typer.Argument(help="Model name in PascalCase (e.g. Product)")],
    fields: Annotated[
        list[str] | None,
        typer.Option("--fields", "-f", help="Fields: name:type (e.g. title:str price:decimal)"),
    ] = None,
    app: Annotated[
        str | None,
        typer.Option("--app", "-a", help="Django app name (default: auto-detect)"),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
    empty: Annotated[
        bool,
        typer.Option("--empty", help="Allow model with no fields"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without creating files"),
    ] = False,
) -> None:
    """Generate a Django model + ninja schema + ninja-extra controller."""
    start = time.monotonic()
    project_root = _find_project_root(path or Path.cwd())
    app_name = _detect_django_app(project_root, app)

    if not fields and not empty:
        print_error("No --fields given. Pass at least one field or use --empty to allow an empty model.")
        raise typer.Exit(code=1)

    parsed = _parse_fields(fields or [])
    pascal = _to_pascal(name)
    snake = _to_snake(name)

    # Validate FK targets exist in the backend models directory
    backend = project_root / "backend"
    if backend.is_dir() and not dry_run:
        for fname, ftype, fk_target in parsed:
            if ftype == "fk" and fk_target:
                target_snake = _to_snake(fk_target)
                target_file = backend / "apps" / app_name / "models" / f"{target_snake}.py"
                if not target_file.exists():
                    print_error(
                        f"FK target '{fk_target}' not found: {target_file}\n"
                        f"Generate it first with: mattstack generate model {fk_target} --fields ..."
                    )
                    raise typer.Exit(code=1)

    if dry_run:
        print_info(f"[dry-run] Would generate model '{pascal}' in app '{app_name}'")

    if not backend.is_dir() and not dry_run:
        print_error(f"No backend/ directory found at {project_root}")
        raise typer.Exit(code=1)

    created: list[Path] = []
    updated: list[Path] = []
    wiring_warnings: list[str] = []

    # Model file
    model_dir = backend / "apps" / app_name / "models"
    model_file = model_dir / f"{snake}.py"
    _ensure_dir(model_dir, dry_run=dry_run)
    _ensure_init(model_dir, dry_run=dry_run)
    _write_file(model_file, _generate_django_model(name, parsed), dry_run=dry_run)
    created.append(model_file)

    # Schema file
    schema_dir = backend / "apps" / app_name / "schemas"
    schema_file = schema_dir / f"{snake}.py"
    _ensure_dir(schema_dir, dry_run=dry_run)
    _ensure_init(schema_dir, dry_run=dry_run)
    _write_file(schema_file, _generate_pydantic_schema(name, parsed), dry_run=dry_run)
    created.append(schema_file)

    # Controller file
    api_dir = backend / "apps" / app_name / "api"
    api_file = api_dir / f"{snake}.py"
    _ensure_dir(api_dir, dry_run=dry_run)
    _ensure_init(api_dir, dry_run=dry_run)
    _write_file(api_file, _generate_api_controller(name, parsed, app_name), dry_run=dry_run)
    created.append(api_file)

    # --- Auto-wiring ---

    # models/__init__.py
    models_init = model_dir / "__init__.py"
    import_line = f"from .{snake} import {pascal}"
    if _update_init_import(models_init, import_line, dry_run=dry_run):
        updated.append(models_init)

    # admin/{snake}_admin.py + admin/__init__.py
    admin_dir = backend / "apps" / app_name / "admin"
    admin_file = admin_dir / f"{snake}_admin.py"
    _ensure_dir(admin_dir, dry_run=dry_run)
    _ensure_init(admin_dir, dry_run=dry_run)
    _write_file(admin_file, _build_admin_file(pascal, snake, app_name, parsed), dry_run=dry_run)
    created.append(admin_file)

    admin_init = admin_dir / "__init__.py"
    admin_import = f"from .{snake}_admin import {pascal}Admin"
    if _update_init_import(admin_init, admin_import, dry_run=dry_run):
        updated.append(admin_init)

    # api/urls.py — best-effort register_controllers update
    urls_file = backend / "api" / "urls.py"
    if not dry_run and urls_file.exists():
        urls_text = urls_file.read_text()
        if "register_controllers" in urls_text and f"{pascal}Controller" not in urls_text:
            wiring_warnings.append(
                f"Register {pascal}Controller in {urls_file}: "
                f"add it to api.register_controllers(...)"
            )
        elif "register_controllers" not in urls_text:
            wiring_warnings.append(f"Wire {pascal}Controller in {urls_file} manually.")
    elif not dry_run:
        wiring_warnings.append(f"No api/urls.py found — register {pascal}Controller manually.")

    # Output
    if not dry_run:
        for f in created:
            print_success(f"Created {f}")
        for f in updated:
            print_success(f"Updated {f}")

    elapsed = time.monotonic() - start
    console.print(
        f"\n[bold]Next steps:[/bold]\n"
        f"  cd backend && uv run python manage.py makemigrations && uv run python manage.py migrate"
    )
    if wiring_warnings:
        for w in wiring_warnings:
            print_warning(w)
    console.print(f"[dim]Completed in {elapsed:.2f}s[/dim]")


@generate_app.command("endpoint")
def endpoint(
    route_path: Annotated[str, typer.Argument(help="URL path (e.g. /products)")],
    method: Annotated[
        str,
        typer.Option("--method", "-m", help="HTTP method: GET, POST, PUT, DELETE"),
    ] = "GET",
    auth: Annotated[
        bool,
        typer.Option("--auth", help="Require authentication"),
    ] = False,
    app: Annotated[
        str | None,
        typer.Option("--app", "-a", help="Django app name"),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without creating files"),
    ] = False,
) -> None:
    """Generate a ninja-extra API endpoint method."""
    start = time.monotonic()
    method = method.upper()
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        print_error(f"Invalid method '{method}'. Use GET, POST, PUT, PATCH, or DELETE.")
        raise typer.Exit(code=1)

    project_root = _find_project_root(path or Path.cwd())
    app_name = _detect_django_app(project_root, app)

    segment = route_path.strip("/").split("/")[0].replace("-", "_")
    if not segment:
        segment = "root"

    backend = project_root / "backend"
    api_dir = backend / "apps" / app_name / "api"
    controller_file = api_dir / f"{segment}.py"

    endpoint_method = _generate_endpoint_method(route_path, method, auth)

    if dry_run:
        print_info(f"[dry-run] Would add {method} {route_path} to {controller_file}")
        console.print(f"\n[dim]{endpoint_method}[/dim]")
    else:
        _ensure_dir(api_dir, dry_run=False)
        _ensure_init(api_dir, dry_run=False)

        if controller_file.exists():
            existing = controller_file.read_text()
            if not existing.endswith("\n"):
                existing += "\n"
            controller_file.write_text(existing + "\n" + endpoint_method)
            print_success(f"Appended {method} {route_path} to {controller_file}")
        else:
            _write_file(controller_file, _generate_controller_file(segment, endpoint_method, auth), dry_run=False)
            print_success(f"Created {controller_file}")

    elapsed = time.monotonic() - start
    console.print(f"[dim]Completed in {elapsed:.2f}s[/dim]")


@generate_app.command("component")
def component(
    name: Annotated[str, typer.Argument(help="Component name in PascalCase (e.g. ProductCard)")],
    comp_path: Annotated[
        str,
        typer.Option("--path", help="Target directory relative to frontend/"),
    ] = "src/components",
    with_test: Annotated[
        bool,
        typer.Option("--with-test", help="Also create a test file"),
    ] = False,
    project_path: Annotated[
        Path | None,
        typer.Option("--project", help="Project root path"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without creating files"),
    ] = False,
) -> None:
    """Generate a React TypeScript component."""
    start = time.monotonic()
    project_root = _find_project_root(project_path or Path.cwd())
    pascal = _to_pascal(name)

    frontend = project_root / "frontend"
    if not frontend.is_dir() and not dry_run:
        print_error(f"No frontend/ directory found at {project_root}")
        raise typer.Exit(code=1)

    component_dir = frontend / comp_path / pascal
    index_file = component_dir / "index.tsx"

    if dry_run:
        print_info(f"[dry-run] Would create component '{pascal}'")

    _write_file(index_file, _generate_react_component(pascal), dry_run=dry_run)
    if not dry_run:
        print_success(f"Created {index_file}")

    if with_test:
        test_file = component_dir / f"{pascal}.test.tsx"
        _write_file(test_file, _generate_react_test(pascal), dry_run=dry_run)
        if not dry_run:
            print_success(f"Created {test_file}")

    elapsed = time.monotonic() - start
    console.print(f"[dim]Completed in {elapsed:.2f}s[/dim]")


@generate_app.command("page")
def page(
    name: Annotated[str, typer.Argument(help="Page name (e.g. dashboard)")],
    page_path: Annotated[
        str | None,
        typer.Option("--path", help="Target directory relative to frontend/"),
    ] = None,
    project_path: Annotated[
        Path | None,
        typer.Option("--project", help="Project root path"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without creating files"),
    ] = False,
) -> None:
    """Generate a TanStack Router or Next.js page."""
    start = time.monotonic()
    project_root = _find_project_root(project_path or Path.cwd())
    framework = _detect_frontend_framework(project_root)
    snake = _to_snake(name)

    frontend = project_root / "frontend"
    if not frontend.is_dir() and not dry_run:
        print_error(f"No frontend/ directory found at {project_root}")
        raise typer.Exit(code=1)

    if framework == "nextjs":
        target_path = page_path or "app"
        page_dir = frontend / target_path / snake
        page_file = page_dir / "page.tsx"
        content = _generate_nextjs_page(name)
        framework_label = "Next.js"
    else:
        target_path = page_path or "src/routes"
        page_dir = frontend / target_path
        page_file = page_dir / f"{snake}.tsx"
        content = _generate_tanstack_page(name)
        framework_label = "TanStack Router"

    if framework == "unknown":
        print_warning("Could not detect frontend framework, defaulting to TanStack Router")

    if dry_run:
        print_info(f"[dry-run] Would create {framework_label} page '{name}'")

    _write_file(page_file, content, dry_run=dry_run)
    if not dry_run:
        print_success(f"Created {page_file}")

    elapsed = time.monotonic() - start
    console.print(f"[dim]Completed in {elapsed:.2f}s[/dim]")


@generate_app.command("hook")
def hook(
    name: Annotated[str, typer.Argument(help="Hook name (e.g. useProducts)")],
    hook_path: Annotated[
        str,
        typer.Option("--path", help="Target directory relative to frontend/"),
    ] = "src/hooks",
    project_path: Annotated[
        Path | None,
        typer.Option("--project", help="Project root path"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without creating files"),
    ] = False,
) -> None:
    """Generate a React custom hook."""
    start = time.monotonic()
    project_root = _find_project_root(project_path or Path.cwd())

    hook_name = name if name.startswith("use") else f"use{_to_pascal(name)}"

    frontend = project_root / "frontend"
    if not frontend.is_dir() and not dry_run:
        print_error(f"No frontend/ directory found at {project_root}")
        raise typer.Exit(code=1)

    hook_dir = frontend / hook_path
    hook_file = hook_dir / f"{hook_name}.ts"

    if dry_run:
        print_info(f"[dry-run] Would create hook '{hook_name}'")

    _write_file(hook_file, _generate_hook(hook_name), dry_run=dry_run)
    if not dry_run:
        print_success(f"Created {hook_file}")

    elapsed = time.monotonic() - start
    console.print(f"[dim]Completed in {elapsed:.2f}s[/dim]")


@generate_app.command("schema")
def schema(
    name: Annotated[str, typer.Argument(help="Schema name in PascalCase (e.g. Product)")],
    fields: Annotated[
        list[str] | None,
        typer.Option("--fields", "-f", help="Fields: name:type (e.g. title:str price:decimal)"),
    ] = None,
    app: Annotated[
        str | None,
        typer.Option("--app", "-a", help="Django app name"),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Project root path"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without creating files"),
    ] = False,
) -> None:
    """Generate ninja schemas (Base/Create/Update/Response) without a Django model."""
    start = time.monotonic()
    project_root = _find_project_root(path or Path.cwd())
    app_name = _detect_django_app(project_root, app)
    parsed = _parse_fields(fields or [])
    pascal = _to_pascal(name)
    snake = _to_snake(name)

    backend = project_root / "backend"
    if not backend.is_dir() and not dry_run:
        print_error(f"No backend/ directory found at {project_root}")
        raise typer.Exit(code=1)

    schema_dir = backend / "apps" / app_name / "schemas"
    schema_file = schema_dir / f"{snake}.py"

    if dry_run:
        print_info(f"[dry-run] Would create schemas for '{pascal}' in app '{app_name}'")

    _ensure_dir(schema_dir, dry_run=dry_run)
    _ensure_init(schema_dir, dry_run=dry_run)
    _write_file(schema_file, _generate_pydantic_schema(name, parsed), dry_run=dry_run)

    if not dry_run:
        print_success(f"Created {schema_file}")

    elapsed = time.monotonic() - start
    console.print(f"[dim]Completed in {elapsed:.2f}s[/dim]")
