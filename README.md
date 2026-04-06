# mattstack

CLI to scaffold fullstack monorepos from battle-tested boilerplates, then audit them for quality.

## Install

```bash
uv sync
```

Or install globally:

```bash
uv tool install .
```

Both `mattstack` and `ms` are available as entry points.

## Quick Start

```bash
# Interactive wizard — walks you through every option
mattstack init

# One-liner with preset
mattstack init my-app --preset starter-fullstack

# With iOS client
mattstack init my-app --preset starter-fullstack --ios

# From a YAML config file
mattstack init --config project.yaml

# Specify output directory
mattstack init my-app --preset b2b-fullstack -o ~/projects
```

## Commands

| Command | Description |
|---------|-------------|
| `mattstack init [name]` | Create a new project from boilerplates |
| `mattstack add <component>` | Add frontend/backend/ios to existing project |
| `mattstack upgrade` | Pull latest boilerplate changes into project |
| `mattstack audit [path]` | Run static analysis on a generated project |
| `mattstack dev` | Start all development services (docker, backend, frontend) |
| `mattstack test` | Run tests across backend and frontend |
| `mattstack lint` | Run linters across backend and frontend |
| `mattstack env [action]` | Manage environment variables (.env files) |
| `mattstack doctor` | Check your development environment |
| `mattstack info` | Show available presets and source repos |
| `mattstack context [path]` | Dump project context for AI agents |
| `mattstack client <cmd>` | Frontend package manager wrapper (bun/npm/yarn/pnpm) |
| `mattstack config [action]` | Manage user config (show/path/init) |
| `mattstack completions` | Install shell completions (bash/zsh/fish) |
| `mattstack version` | Show version (with update check) |

### Global Options

| Flag | Description |
|------|-------------|
| `--verbose, -v` | Show detailed output for debugging |
| `--quiet, -q` | Suppress non-essential output (for CI) |

### `init` Options

| Flag | Description |
|------|-------------|
| `--preset, -p` | Use a preset (e.g. `starter-fullstack`, `b2b-api`) |
| `--config, -c` | Path to YAML config file |
| `--ios` | Include iOS client |
| `--output, -o` | Output directory (default: current) |
| `--dry-run` | Preview what would be generated without writing files |

### `add` Options

| Flag | Description |
|------|-------------|
| `--path, -p` | Project path (default: current directory) |
| `--framework, -f` | Frontend framework: `react-vite`, `react-vite-starter`, `react-rsbuild`, `nextjs` |
| `--dry-run` | Preview what would be added |

### `upgrade` Options

| Flag | Description |
|------|-------------|
| `--component, -c` | Upgrade specific component: `backend`, `frontend` |
| `--dry-run` | Preview changes without applying them |
| `--force` | Overwrite modified files (use with caution) |

### `audit` Options

| Flag | Description |
|------|-------------|
| `--type, -t` | Audit type(s): `types`, `quality`, `endpoints`, `tests`, `dependencies`, `vulnerabilities` |
| `--severity, -s` | Minimum severity: `error`, `warning`, `info` |
| `--live` | Enable live endpoint probing (GET only, safe) |
| `--base-url` | Base URL for live probing (default: `http://localhost:8000`) |
| `--no-todo` | Skip writing to `tasks/todo.md` |
| `--json` | Machine-readable JSON output |
| `--html` | Generate browsable HTML dashboard report |
| `--fix` | Auto-remove debug statements (`print()`, `console.log()`) |

```bash
# All audits on current directory
mattstack audit

# Specific project path
mattstack audit /path/to/project

# Type safety only
mattstack audit -t types

# Multiple audit types
mattstack audit -t quality -t tests

# Live endpoint probing (server must be running)
mattstack audit -t endpoints --live

# JSON for CI pipelines
mattstack audit --json

# Auto-fix debug statements
mattstack audit -t quality --fix

# HTML dashboard
mattstack audit --html
```

### `dev` Options

| Flag | Description |
|------|-------------|
| `--path, -p` | Project path (default: current directory) |
| `--services, -s` | Comma-separated services to start: `backend,frontend,docker` |
| `--no-docker` | Skip Docker infrastructure |

```bash
# Start everything (docker + backend + frontend)
mattstack dev

# Backend only
mattstack dev --services backend

# Skip Docker, just start app servers
mattstack dev --no-docker
```

### `test` Options

| Flag | Description |
|------|-------------|
| `--path, -p` | Project path (default: current directory) |
| `--backend-only` | Run backend tests only |
| `--frontend-only` | Run frontend tests only |
| `--coverage` | Run with coverage reporting |
| `--parallel` | Run backend and frontend tests concurrently |

```bash
# Run all tests
mattstack test

# Backend only with coverage
mattstack test --backend-only --coverage

# Run both in parallel
mattstack test --parallel
```

### `lint` Options

| Flag | Description |
|------|-------------|
| `--path, -p` | Project path (default: current directory) |
| `--fix` | Auto-fix lint issues |
| `--format-check` | Also check formatting (ruff format) |
| `--backend-only` | Lint backend only |
| `--frontend-only` | Lint frontend only |

```bash
# Check all
mattstack lint

# Auto-fix everything
mattstack lint --fix

# Check formatting too
mattstack lint --format-check
```

### `env` Actions

| Action | Description |
|--------|-------------|
| `check` (default) | Compare `.env.example` vs `.env`, report missing/extra vars |
| `sync` | Copy missing vars from `.env.example` into `.env` |
| `show` | Display current `.env` vars with masked values |

```bash
# Check for missing env vars
mattstack env check

# Auto-sync missing vars from .env.example
mattstack env sync

# Show current env vars (values masked)
mattstack env show
```

### `context` Options

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON instead of markdown |
| `--output, -o` | Write context to a file |

```bash
# Dump project context for AI agents
mattstack context

# Write to file
mattstack context -o context.md
```

### `client` Subcommands

Unified frontend package manager wrapper — auto-detects bun/npm/yarn/pnpm from lockfiles.

| Subcommand | Description |
|------------|-------------|
| `client add <packages>` | Add packages (`-D` for dev) |
| `client remove <packages>` | Remove packages |
| `client install` | Install all dependencies |
| `client run <script>` | Run a package.json script |
| `client dev` | Start frontend dev server |
| `client build` | Build for production |
| `client exec <binary>` | Run binary (bunx/npx) |
| `client which` | Show detected package manager |

```bash
# Add a dependency
mattstack client add zustand

# Run a script
mattstack client run generate

# Check which package manager
mattstack client which
```

### `completions`

```bash
# Show instructions
mattstack completions

# Install for your shell (bash/zsh/fish)
mattstack completions --install

# Show completion script
mattstack completions --show
```

## Presets

| Preset | Type | Description |
|--------|------|-------------|
| `starter-fullstack` | fullstack | Django Ninja + React Vite (TanStack Router) |
| `b2b-fullstack` | fullstack | B2B variant with orgs, teams, RBAC |
| `starter-api` | backend-only | Django Ninja API |
| `b2b-api` | backend-only | B2B backend with orgs, teams, RBAC |
| `starter-frontend` | frontend-only | React Vite (TanStack Router) |
| `simple-frontend` | frontend-only | React Vite (React Router, simpler) |
| `rsbuild-fullstack` | fullstack | Django Ninja + React Rsbuild |
| `rsbuild-frontend` | frontend-only | React Rsbuild SPA (TanStack Router) |
| `nextjs-fullstack` | fullstack | Django Ninja + Next.js (App Router) |
| `nextjs-frontend` | frontend-only | Next.js standalone (App Router, Tailwind) |

## Audit Domains

### 1. `types` — Pydantic ↔ TS/Zod sync

Parses Pydantic schemas from the backend and TypeScript interfaces + Zod schemas from the frontend, then compares:

- **Field presence**: finds fields in Python missing from TS/Zod (snake_case → camelCase aware)
- **Type compatibility**: `str → string`, `int → number`, `bool → boolean`, etc.
- **Optionality**: `Optional[str]` vs `field?: string`
- **Constraint sync**: `Field(min_length=3)` vs `.min(3)`

### 2. `quality` — Code quality

Scans all `.py`, `.ts`, `.tsx`, `.js`, `.jsx` files for:

- TODO/FIXME/HACK/XXX comments
- Stub functions (`pass`, `...`, `raise NotImplementedError`)
- Mock/placeholder data (`mock_`, `fake_`, `lorem ipsum`, hardcoded `localhost`)
- Hardcoded credentials (`admin/admin`, `password123`, `test@test.com`)
- Debug statements (`print()`, `console.log()`, `breakpoint()`, `debugger`)

### 3. `endpoints` — Route verification

- **Static**: parses `@router.get()` / `@http_get()` decorators, finds duplicates, missing auth on write endpoints, stub handlers
- **Live** (`--live`): GET-probes discovered endpoints, reports 500s and 404s (safe, read-only, never sends POST/PUT/DELETE)

### 4. `tests` — Coverage gaps

- Parses pytest (`test_*.py`) and vitest (`*.test.ts`) files
- Maps tests to feature areas (auth, user, crud, org)
- Finds schemas with no corresponding tests
- Reports empty test files and naming issues
- Suggests user story groupings for sparse areas

### 5. `dependencies` — Version compatibility

- Parses `pyproject.toml` (regex-based) and `package.json` for dependency info
- Finds unpinned dependencies (no version constraint)
- Detects overly broad constraints (`>=` without upper bound)
- Warns about deprecated packages (`nose`, `mock`, `moment`, `tslint`, etc.)
- Catches duplicate dependencies across regular/dev
- Flags TypeScript version conflicts across manifests

### 6. `vulnerabilities` — Known CVEs

- Runs `pip-audit` (Python) and `npm audit` (JS) if available
- Falls back to OSV API for vulnerability lookup
- Reports known CVEs with severity and fix versions

### Custom Auditors (Plugin System)

Drop `.py` files into `mattstack-plugins/` in your project root to add custom audit rules. Each file should export a class that inherits `BaseAuditor`:

```python
from mattstack.auditors.base import AuditType, BaseAuditor, Severity

class MyCustomAuditor(BaseAuditor):
    audit_type = AuditType.QUALITY  # or any AuditType

    def run(self):
        # your custom checks here
        return self.findings
```

## Generated Project Structure

```
my-app/
├── backend/                          # Django Ninja API
├── frontend/                         # React + Vite + TanStack Router
├── ios/                              # Swift iOS client (optional, auto-renamed)
├── docker-compose.yml
├── docker-compose.prod.yml
├── docker-compose.override.yml.example  # Per-developer customization
├── .pre-commit-config.yaml           # ruff + prettier hooks
├── Makefile                          # All commands: setup, up, test, lint, format
├── .env.example
├── .gitignore
├── CLAUDE.md                         # AI assistant context
├── README.md
└── tasks/
    └── todo.md                       # Audit findings land here
```

## iOS Support

Include an iOS client with any fullstack project:

```bash
# During project creation
mattstack init my-app --preset starter-fullstack --ios

# Add to an existing project
mattstack add ios --path /path/to/project
```

The iOS client is cloned from [swift-ios-starter](https://github.com/mattjaikaran/swift-ios-starter) and auto-renamed from the default `MyApp` to match your project's display name. It targets SwiftUI with iOS 17+ and uses the MVVM pattern.

**Backend networking**: The generated iOS project includes an API client configured with a base URL constant. Update it to point at your backend (e.g. `http://localhost:8000` for local development).

**Audit limitation**: The `mattstack audit` command does not yet scan `.swift` files. Type safety, quality, and test auditors currently cover Python and TypeScript only.

## Source Repositories

| Key | Repository |
|-----|-----------|
| `django-ninja` | [django-ninja-boilerplate](https://github.com/mattjaikaran/django-ninja-boilerplate) |
| `react-vite` | [react-vite-boilerplate](https://github.com/mattjaikaran/react-vite-boilerplate) |
| `react-vite-starter` | [react-vite-starter](https://github.com/mattjaikaran/react-vite-starter) |
| `react-rsbuild` | [react-rsbuild-boilerplate](https://github.com/mattjaikaran/react-rsbuild-boilerplate) |
| `swift-ios` | [swift-ios-starter](https://github.com/mattjaikaran/swift-ios-starter) |

## Architecture

```
src/mattstack/
├── cli.py              # Typer app — all commands
├── config.py           # Enums, ProjectConfig, REPO_URLS
├── presets.py           # 8 preset definitions
├── commands/
│   ├── init.py         # Interactive wizard + routing
│   ├── add.py          # Add components to existing projects
│   ├── upgrade.py      # Pull latest boilerplate changes
│   ├── audit.py        # Audit orchestrator
│   ├── dev.py          # Unified dev server start
│   ├── test.py         # Unified test runner
│   ├── lint.py         # Unified linter
│   ├── env.py          # Environment variable management
│   ├── context.py      # AI agent context dump
│   ├── client.py       # Frontend package manager wrapper
│   ├── doctor.py       # Environment validation
│   ├── info.py         # Preset display
│   ├── version.py      # Version + update check
│   └── completions.py  # Shell completion installer
├── generators/
│   ├── base.py         # BaseGenerator (clone, strip, write)
│   ├── fullstack.py    # 8-step fullstack generation
│   ├── backend_only.py # 6-step backend generation
│   ├── frontend_only.py# 5-step frontend generation
│   └── ios.py          # iOS helper (auto-renames MyApp references)
├── auditors/
│   ├── base.py             # AuditFinding, AuditConfig, BaseAuditor
│   ├── types.py            # Pydantic ↔ TS/Zod comparison
│   ├── quality.py          # TODOs, stubs, debug, credentials
│   ├── endpoints.py        # Route analysis + live probing
│   ├── tests.py            # Coverage gaps + feature mapping
│   ├── dependencies.py     # pyproject.toml + package.json checks
│   ├── vulnerabilities.py  # CVE scanning (pip-audit, npm audit, OSV)
│   ├── report.py           # Rich tables + todo.md writer
│   ├── html_report.py      # Standalone HTML dashboard export
│   └── plugins.py          # Custom auditor plugin loader
├── parsers/
│   ├── python_schemas.py    # Pydantic class parser
│   ├── typescript_types.py  # TS interface parser
│   ├── zod_schemas.py       # Zod z.object() parser
│   ├── django_routes.py     # Route decorator parser
│   ├── test_files.py        # pytest/vitest parser
│   └── dependencies.py      # pyproject.toml + package.json parser
├── post_processors/
│   ├── customizer.py   # Rename backend/frontend
│   ├── frontend_config.py # Monorepo .env + vite config
│   └── b2b.py          # B2B feature instructions
├── templates/           # f-string template functions (all conditional on feature flags)
│                        # makefile, docker_compose, env, readme, gitignore, claude_md
│                        # pre_commit_config, docker_compose_override
│                        # deploy_railway, deploy_render, deploy_cloudflare, deploy_digitalocean
└── utils/               # console, git, docker, process, yaml_config
```

## Ecosystem

mattstack is extensible -- bring your own boilerplates, presets, and audit plugins.

- **Custom repos & presets**: `~/.mattstack/config.yaml` -- see [Ecosystem Guide](docs/ecosystem.md)
- **Audit plugins**: Drop `.py` files in `mattstack-plugins/` -- see [Plugin Guide](docs/plugin-guide.md)
- **Deployment targets**: 8 platforms supported -- see [Deployment Guide](docs/deployment-guide.md)

```bash
mattstack config init   # Create user config template
mattstack config show   # View current config
```

## Development

```bash
uv sync                        # Install dependencies
uv run pytest -x -q            # Run tests (586 tests)
uv run pytest --cov            # With coverage
uv run ruff check src/ tests/  # Lint
uv run ruff format src/ tests/ # Format
```

## License

MIT
