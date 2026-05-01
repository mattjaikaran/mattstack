"""Context command group: dump project context for AI agents."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated

import typer

from mattstack.utils.console import console
from mattstack.utils.package_manager import detect_package_manager
from mattstack.utils.process import command_available, get_command_version

context_app = typer.Typer(
    help="Dump project context for AI agents (Claude, Cursor, etc.).",
    no_args_is_help=True,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _detect_components(path: Path) -> dict[str, bool]:
    return {
        "backend": (path / "backend" / "pyproject.toml").exists(),
        "frontend": (path / "frontend" / "package.json").exists(),
        "ios": (path / "ios").is_dir() and any((path / "ios").glob("*.xcodeproj")),
        "docker": (path / "docker-compose.yml").exists(),
        "makefile": (path / "Makefile").exists(),
        "claude_md": (path / "CLAUDE.md").exists(),
    }


def _detect_backend_stack(path: Path) -> dict:
    backend_dir = path / "backend"
    if not (backend_dir / "pyproject.toml").exists():
        return {}
    info: dict = {"language": "python", "package_manager": "uv"}
    content = (backend_dir / "pyproject.toml").read_text(encoding="utf-8")
    if "django" in content.lower():
        info["framework"] = "django"
    if "django-ninja" in content.lower():
        info["api"] = "django-ninja"
    if "celery" in content.lower():
        info["task_queue"] = "celery"
    return info


def _detect_frontend_stack(path: Path) -> dict:
    pkg_json = path / "frontend" / "package.json"
    if not pkg_json.exists():
        return {}
    try:
        pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    pm = detect_package_manager(path)
    info: dict = {"language": "typescript", "package_manager": pm.value}
    if "next" in deps:
        info["framework"] = "next.js"
    elif "vite" in deps:
        info["framework"] = "vite"
    if "react" in deps:
        info["ui_library"] = "react"
    if "tailwindcss" in deps or "@tailwindcss/vite" in deps:
        info["styling"] = "tailwind"
    scripts = pkg.get("scripts", {})
    if scripts:
        info["scripts"] = list(scripts.keys())
    return info


def _detect_env_vars(path: Path) -> list[str]:
    env_example = path / ".env.example"
    if not env_example.exists():
        return []
    names = []
    for line in env_example.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            names.append(line.split("=", 1)[0].strip())
    return names


def _detect_makefile_targets(path: Path) -> list[str]:
    makefile = path / "Makefile"
    if not makefile.exists():
        return []
    targets = []
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("\t") and not line.startswith("#") and ":" in line:
            target = line.split(":")[0].strip()
            if target and not target.startswith("."):
                targets.append(target)
    return targets


def _tool_versions() -> dict[str, str | None]:
    tools = ["git", "uv", "bun", "node", "python", "docker", "make"]
    versions = {}
    for tool in tools:
        if command_available(tool):
            ver = get_command_version(tool)
            versions[tool] = ver.split("\n")[0] if ver else "installed"
    return versions


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


# ── stack context (original behaviour) ───────────────────────────────────────

def build_stack_context(path: Path) -> dict:
    components = _detect_components(path)
    ctx: dict = {
        "project_name": path.name,
        "project_path": str(path.resolve()),
        "components": components,
    }
    if components["backend"]:
        ctx["backend"] = _detect_backend_stack(path)
    if components["frontend"]:
        ctx["frontend"] = _detect_frontend_stack(path)
    env_vars = _detect_env_vars(path)
    if env_vars:
        ctx["env_vars"] = env_vars
    targets = _detect_makefile_targets(path)
    if targets:
        ctx["makefile_targets"] = targets
    ctx["tools"] = _tool_versions()
    return ctx


# legacy alias for other code that imports build_context
build_context = build_stack_context


# ── models context ────────────────────────────────────────────────────────────

def build_models_context(path: Path) -> dict:
    from mattstack.parsers.django_models import find_model_files, parse_models_file

    model_files = find_model_files(path)
    models_out = []
    for mf in model_files:
        try:
            for m in parse_models_file(mf):
                fields_out = [
                    {"name": f.name, "type": f.field_type, **f.kwargs}
                    for f in m.fields
                ]
                models_out.append(
                    {
                        "name": m.name,
                        "app": m.app,
                        "file": str(mf.relative_to(path)),
                        "inherits": m.inherits,
                        "fields": fields_out,
                    }
                )
        except OSError:
            pass
    return {"models": models_out}


# ── routes context ────────────────────────────────────────────────────────────

def build_routes_context(path: Path) -> dict:
    from mattstack.parsers.django_routes import find_controller_files, parse_controller_file

    controller_files = find_controller_files(path)
    routes_out = []
    for cf in controller_files:
        try:
            for c in parse_controller_file(cf):
                endpoints = [
                    {
                        "method": ep.method,
                        "path": ep.path,
                        "handler": ep.handler,
                        "response": ep.response,
                        "auth": ep.auth,
                    }
                    for ep in c.endpoints
                ]
                routes_out.append(
                    {
                        "controller": c.name,
                        "prefix": c.prefix,
                        "tag": c.tag,
                        "file": str(cf.relative_to(path)),
                        "endpoints": endpoints,
                    }
                )
        except OSError:
            pass
    return {"routes": routes_out}


# ── types context ─────────────────────────────────────────────────────────────

def build_types_context(path: Path) -> dict:
    from mattstack.parsers.typescript_types import find_typescript_type_files, parse_typescript_file
    from mattstack.parsers.zod_schemas import find_zod_files, parse_zod_file

    ts_files = find_typescript_type_files(path)
    interfaces_out = []
    for tf in ts_files:
        try:
            for iface in parse_typescript_file(tf):
                fields_out = [
                    {"name": f.name, "type": f.type_str, "optional": f.optional}
                    for f in iface.fields
                ]
                interfaces_out.append(
                    {
                        "name": iface.name,
                        "file": str(tf.relative_to(path)),
                        "extends": iface.extends,
                        "fields": fields_out,
                    }
                )
        except OSError:
            pass

    zod_files = find_zod_files(path)
    zod_out = []
    for zf in zod_files:
        try:
            for schema in parse_zod_file(zf):
                fields_out = [
                    {"name": f.name, "type": f.type_str, "optional": f.optional}
                    for f in schema.fields
                ]
                zod_out.append(
                    {
                        "name": schema.name,
                        "file": str(zf.relative_to(path)),
                        "fields": fields_out,
                    }
                )
        except OSError:
            pass

    return {"interfaces": interfaces_out, "zod_schemas": zod_out}


# ── full context ──────────────────────────────────────────────────────────────

def build_full_context(path: Path) -> dict:
    ctx = build_stack_context(path)
    ctx.update(build_models_context(path))
    ctx.update(build_routes_context(path))
    ctx.update(build_types_context(path))
    return ctx


# ── formatters ────────────────────────────────────────────────────────────────

def format_context_markdown(ctx: dict) -> str:
    lines = [f"# Project: {ctx.get('project_name', 'unknown')}", ""]
    comps = ctx.get("components", {})
    active = [k for k, v in comps.items() if v]
    if active:
        lines += [f"**Components:** {', '.join(active)}", ""]
    if "backend" in ctx:
        lines.append("## Backend")
        for k, v in ctx["backend"].items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")
    if "frontend" in ctx:
        lines.append("## Frontend")
        for k, v in ctx["frontend"].items():
            if k == "scripts":
                lines.append(f"- **scripts:** {', '.join(v)}")
            else:
                lines.append(f"- **{k}:** {v}")
        lines.append("")
    if "env_vars" in ctx:
        lines += ["## Environment Variables", f"`{', '.join(ctx['env_vars'])}`", ""]
    if "makefile_targets" in ctx:
        lines += ["## Makefile Targets", f"`{', '.join(ctx['makefile_targets'])}`", ""]
    if "tools" in ctx:
        lines.append("## Dev Tools")
        for tool, ver in ctx["tools"].items():
            lines.append(f"- **{tool}:** {ver}")
        lines.append("")
    if "models" in ctx and ctx["models"]:
        lines.append("## Models")
        for m in ctx["models"]:
            field_names = ", ".join(f["name"] for f in m.get("fields", []))
            inherits = m["inherits"]
            flds = field_names or "none"
            lines.append(
                f"- **{m['name']}** ({m['app']}) inherits `{inherits}` — fields: {flds}"
            )
        lines.append("")
    if "routes" in ctx and ctx["routes"]:
        lines.append("## API Routes")
        for c in ctx["routes"]:
            lines.append(f"### {c['controller']} — `{c['prefix']}`")
            for ep in c.get("endpoints", []):
                auth_mark = " 🔒" if ep["auth"] else ""
                resp = f" → {ep['response']}" if ep["response"] else ""
                lines.append(f"  - `{ep['method']} {c['prefix']}{ep['path']}`{resp}{auth_mark}")
        lines.append("")
    if "interfaces" in ctx and ctx["interfaces"]:
        lines.append("## TypeScript Interfaces")
        for iface in ctx["interfaces"]:
            field_names = ", ".join(f["name"] for f in iface.get("fields", []))
            lines.append(f"- **{iface['name']}** — {field_names or 'no fields'}")
        lines.append("")
    return "\n".join(lines)


def format_context_claude(ctx: dict) -> str:
    """Wrap context in Claude XML blocks."""
    parts = ["<context>"]
    if "project_name" in ctx:
        name = ctx["project_name"]
        path_val = ctx.get("project_path", "")
        parts.append(f'  <project name="{name}" path="{path_val}">')
        comps = ctx.get("components", {})
        active = [k for k, v in comps.items() if v]
        if active:
            parts.append(f"    <components>{', '.join(active)}</components>")
        parts.append("  </project>")
    if "models" in ctx and ctx["models"]:
        parts.append("  <models>")
        for m in ctx["models"]:
            parts.append(
                f"    <model name=\"{m['name']}\" app=\"{m['app']}\" inherits=\"{m['inherits']}\">"
            )
            for f in m.get("fields", []):
                kwargs = " ".join(
                    f'{k}="{v}"' for k, v in f.items() if k not in ("name", "type")
                )
                parts.append(f"      <field name=\"{f['name']}\" type=\"{f['type']}\" {kwargs}/>")
            parts.append("    </model>")
        parts.append("  </models>")
    if "routes" in ctx and ctx["routes"]:
        parts.append("  <routes>")
        for c in ctx["routes"]:
            tag_attr = f" tag=\"{c['tag']}\"" if c["tag"] else ""
            ctrl = c["controller"]
            pfx = c["prefix"]
            parts.append(f'    <controller name="{ctrl}" prefix="{pfx}"{tag_attr}>')
            for ep in c.get("endpoints", []):
                auth_attr = " auth=\"true\"" if ep["auth"] else ""
                resp_attr = f" response=\"{ep['response']}\"" if ep["response"] else ""
                parts.append(
                    f"      <endpoint method=\"{ep['method']}\" path=\"{ep['path']}\""
                    f" handler=\"{ep['handler']}\"{resp_attr}{auth_attr}/>"
                )
            parts.append("    </controller>")
        parts.append("  </routes>")
    if "interfaces" in ctx and ctx["interfaces"]:
        parts.append("  <types>")
        for iface in ctx["interfaces"]:
            ext = f" extends=\"{iface['extends']}\"" if iface["extends"] else ""
            parts.append(f"    <interface name=\"{iface['name']}\"{ext}>")
            for f in iface.get("fields", []):
                opt = " optional=\"true\"" if f["optional"] else ""
                parts.append(f"      <field name=\"{f['name']}\" type=\"{f['type']}\"{opt}/>")
            parts.append("    </interface>")
        parts.append("  </types>")
    if "zod_schemas" in ctx and ctx["zod_schemas"]:
        parts.append("  <zod_schemas>")
        for schema in ctx["zod_schemas"]:
            parts.append(f"    <schema name=\"{schema['name']}\">")
            for f in schema.get("fields", []):
                opt = " optional=\"true\"" if f["optional"] else ""
                parts.append(f"      <field name=\"{f['name']}\" type=\"{f['type']}\"{opt}/>")
            parts.append("    </schema>")
        parts.append("  </zod_schemas>")
    parts.append("</context>")
    return "\n".join(parts)


def _apply_format(ctx: dict, fmt: str, include_token_count: bool = True) -> str:
    if fmt == "json":
        if include_token_count:
            text = json.dumps(ctx, indent=2)
            ctx_with_tokens = {**ctx, "_estimated_tokens": estimate_tokens(text)}
            return json.dumps(ctx_with_tokens, indent=2)
        return json.dumps(ctx, indent=2)
    elif fmt == "claude":
        text = format_context_claude(ctx)
    else:
        text = format_context_markdown(ctx)
    if include_token_count:
        tokens = estimate_tokens(text)
        text += f"\n\n# Estimated tokens: ~{tokens:,}"
    return text


def _truncate_to_tokens(ctx: dict, max_tokens: int, fmt: str) -> dict:
    """Naively trim lists in ctx until estimated token count fits."""
    text = _apply_format(ctx, fmt, include_token_count=False)
    if estimate_tokens(text) <= max_tokens:
        return ctx
    # Trim models / routes / interfaces
    for key in ("models", "routes", "interfaces", "zod_schemas"):
        if key in ctx and isinstance(ctx[key], list):
            while ctx[key] and estimate_tokens(_apply_format(ctx, fmt, False)) > max_tokens:
                ctx[key] = ctx[key][:-1]
    return ctx


def _output(text: str, output_file: str | None) -> None:
    if output_file:
        out = Path(output_file)
        out.write_text(text, encoding="utf-8")
        from mattstack.utils.console import print_success
        print_success(f"Context written to {out}")
    else:
        console.print(text)


# ── watch helper ──────────────────────────────────────────────────────────────

def _watch_loop(path: Path, builder, fmt: str, max_tokens: int | None) -> None:
    """Poll for file changes and re-emit context."""
    import contextlib
    import os

    def _snapshot() -> dict[str, float]:
        snap: dict[str, float] = {}
        for p in path.rglob("*.py"):
            with contextlib.suppress(OSError):
                snap[str(p)] = os.path.getmtime(p)
        for p in path.rglob("*.ts"):
            with contextlib.suppress(OSError):
                snap[str(p)] = os.path.getmtime(p)
        return snap

    def _emit() -> None:
        import datetime
        console.print(f"\n[dim]── {datetime.datetime.now().strftime('%H:%M:%S')} ──[/dim]")
        ctx = builder(path)
        if max_tokens:
            ctx = _truncate_to_tokens(ctx, max_tokens, fmt)
        console.print(_apply_format(ctx, fmt))

    _emit()
    snap = _snapshot()
    console.print("[dim]Watching for changes... (Ctrl-C to stop)[/dim]")
    try:
        while True:
            time.sleep(1)
            new_snap = _snapshot()
            if new_snap != snap:
                snap = new_snap
                _emit()
    except KeyboardInterrupt:
        pass


# ── common options ────────────────────────────────────────────────────────────

_FMT_HELP = "Output format: markdown (default), json, claude"
_PATH_HELP = "Project path (default: current directory)"
_OUTPUT_HELP = "Write output to a file"
_MAX_TOKENS_HELP = "Truncate output to approximately N tokens"
_WATCH_HELP = "Re-emit context on file changes (poll mode)"


# ── subcommands ───────────────────────────────────────────────────────────────

@context_app.command("stack")
def cmd_stack(
    path: Annotated[Path | None, typer.Argument(help=_PATH_HELP)] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help=_FMT_HELP)] = "markdown",
    output: Annotated[str | None, typer.Option("--output", "-o", help=_OUTPUT_HELP)] = None,
    max_tokens: Annotated[int | None, typer.Option("--max-tokens", help=_MAX_TOKENS_HELP)] = None,
) -> None:
    """Tech stack summary (languages, frameworks, tools)."""
    p = path or Path.cwd()
    ctx = build_stack_context(p)
    if max_tokens:
        ctx = _truncate_to_tokens(ctx, max_tokens, fmt)
    _output(_apply_format(ctx, fmt), output)


@context_app.command("models")
def cmd_models(
    path: Annotated[Path | None, typer.Argument(help=_PATH_HELP)] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help=_FMT_HELP)] = "markdown",
    output: Annotated[str | None, typer.Option("--output", "-o", help=_OUTPUT_HELP)] = None,
    max_tokens: Annotated[int | None, typer.Option("--max-tokens", help=_MAX_TOKENS_HELP)] = None,
) -> None:
    """All Django models with field types as structured output."""
    p = path or Path.cwd()
    ctx = build_models_context(p)
    if max_tokens:
        ctx = _truncate_to_tokens(ctx, max_tokens, fmt)
    _output(_apply_format(ctx, fmt), output)


@context_app.command("routes")
def cmd_routes(
    path: Annotated[Path | None, typer.Argument(help=_PATH_HELP)] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help=_FMT_HELP)] = "markdown",
    output: Annotated[str | None, typer.Option("--output", "-o", help=_OUTPUT_HELP)] = None,
    max_tokens: Annotated[int | None, typer.Option("--max-tokens", help=_MAX_TOKENS_HELP)] = None,
) -> None:
    """All API routes with methods, paths, controller, and auth."""
    p = path or Path.cwd()
    ctx = build_routes_context(p)
    if max_tokens:
        ctx = _truncate_to_tokens(ctx, max_tokens, fmt)
    _output(_apply_format(ctx, fmt), output)


@context_app.command("types")
def cmd_types(
    path: Annotated[Path | None, typer.Argument(help=_PATH_HELP)] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help=_FMT_HELP)] = "markdown",
    output: Annotated[str | None, typer.Option("--output", "-o", help=_OUTPUT_HELP)] = None,
    max_tokens: Annotated[int | None, typer.Option("--max-tokens", help=_MAX_TOKENS_HELP)] = None,
) -> None:
    """All TypeScript interfaces and Zod schemas."""
    p = path or Path.cwd()
    ctx = build_types_context(p)
    if max_tokens:
        ctx = _truncate_to_tokens(ctx, max_tokens, fmt)
    _output(_apply_format(ctx, fmt), output)


@context_app.command("full")
def cmd_full(
    path: Annotated[Path | None, typer.Argument(help=_PATH_HELP)] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help=_FMT_HELP)] = "markdown",
    output: Annotated[str | None, typer.Option("--output", "-o", help=_OUTPUT_HELP)] = None,
    max_tokens: Annotated[int | None, typer.Option("--max-tokens", help=_MAX_TOKENS_HELP)] = None,
    watch: Annotated[bool, typer.Option("--watch", "-w", help=_WATCH_HELP)] = False,
) -> None:
    """Stack + models + routes + types — full AI agent context."""
    p = path or Path.cwd()
    if watch:
        _watch_loop(p, build_full_context, fmt, max_tokens)
        return
    ctx = build_full_context(p)
    if max_tokens:
        ctx = _truncate_to_tokens(ctx, max_tokens, fmt)
    _output(_apply_format(ctx, fmt), output)


# ── legacy run_context kept for backward compat ───────────────────────────────

def run_context(
    path: Path,
    json_output: bool = False,
    output_file: str | None = None,
) -> None:
    """Legacy entry point: dump project context (stack only)."""
    if not path.is_dir():
        from mattstack.utils.console import print_error
        print_error(f"Directory not found: {path}")
        raise typer.Exit(code=1)
    fmt = "json" if json_output else "markdown"
    ctx = build_stack_context(path)
    _output(_apply_format(ctx, fmt), output_file)
