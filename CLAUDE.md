# mattstack

CLI tool to scaffold fullstack monorepos, generate components, sync types, and audit for quality.

## Tech Stack
- Python 3.12+, Typer + Rich + Questionary + PyYAML
- Package manager: `uv` (never pip/poetry)
- Build: hatchling
- Linter: ruff (line-length=100, select E,F,I,N,UP,B,SIM)
- License: Apache-2.0

## CLI Reference (26 commands)

```bash
# Project scaffolding
mattstack init [name]           # Create project (interactive or preset)
mattstack create [name]         # Alias for init
mattstack init my-app -p starter-fullstack  # Preset mode
mattstack init --config f.yaml  # Config file mode
mattstack add frontend          # Add component to existing project
mattstack add frontend -f react-rsbuild-kibo  # Specify framework
mattstack upgrade               # Pull latest boilerplate changes
mattstack upgrade -c backend    # Upgrade specific component

# Code generation
mattstack generate model Product --fields "title:str price:decimal is_active:bool"
mattstack generate endpoint /products --method GET --auth
mattstack generate component ProductCard --with-test
mattstack generate page dashboard
mattstack generate hook useProducts
mattstack generate schema ProductCreate --fields "title:str price:decimal"

# Database management
mattstack db migrate            # Run Django migrations
mattstack db makemigrations     # Create migrations
mattstack db status             # Show migration status
mattstack db seed               # Seed from backend/seed.py
mattstack db seed --fresh       # Flush + migrate + seed
mattstack db reset --seed       # Reset DB (with confirmation)
mattstack db shell              # Django dbshell
mattstack db dump --app users   # Dump fixtures
mattstack db load fixtures.json # Load fixtures

# Type sync (Pydantic → TypeScript/Zod)
mattstack sync types            # Generate TS interfaces from Pydantic
mattstack sync zod              # Generate Zod schemas from Pydantic
mattstack sync api-client       # Generate TanStack Query hooks from Django routes
mattstack sync all              # Run types + zod + api-client

# Dependency management
mattstack deps check            # Show outdated packages
mattstack deps update           # Update both stacks
mattstack deps audit            # Security vulnerability scan

# Service management
mattstack dev                   # Start all services (docker + backend + frontend)
mattstack dev --services backend,frontend  # Start specific services
mattstack health                # Check Docker, DB, Redis, port status
mattstack health --live         # Also probe HTTP endpoints

# Quality
mattstack test                  # Run tests across backend and frontend
mattstack test --parallel       # Run in parallel
mattstack lint                  # Run linters
mattstack lint --parallel       # Parallel lint
mattstack lint --fix            # Auto-fix
mattstack fmt                   # Format all code (lint --fix --format-check)
mattstack audit [path]          # Static analysis (6 domains)
mattstack audit --html          # HTML dashboard report

# Git hooks
mattstack hooks install         # Install pre-commit hooks
mattstack hooks status          # Show installed hooks
mattstack hooks run             # Run all hooks manually

# CI/CD
mattstack workflow              # Generate GitHub Actions CI/CD
mattstack workflow --platform gitlab-ci

# Environment & config
mattstack env check             # Compare .env.example vs .env
mattstack env sync              # Copy missing vars
mattstack doctor                # Check environment
mattstack rules                 # Generate CLAUDE.md, .cursorrules

# Info
mattstack info                  # Show presets and repos
mattstack presets               # Alias for info
mattstack context               # Dump project context for AI agents
mattstack client add zustand    # Frontend package manager wrapper
mattstack version               # Show version
mattstack completions --install # Shell completions
```

## File Map

```
src/mattstack/
├── cli.py              # Typer app — 26 commands, 6 subgroups (client, generate, db, sync, deps, hooks)
├── config.py           # ProjectType, Variant, FrontendFramework (5 values), DeploymentTarget enums
│                       # ProjectConfig dataclass, REPO_URLS (7 repos), normalize_name()
├── presets.py          # 12 presets: starter-fullstack, b2b-fullstack, starter-api, b2b-api,
│                       #   starter-frontend, simple-frontend, rsbuild-fullstack, rsbuild-frontend,
│                       #   kibo-fullstack, kibo-frontend, nextjs-fullstack, nextjs-frontend
│
├── commands/
│   ├── init.py         # run_init() — 3 modes: config-file → preset → interactive wizard
│   ├── add.py          # run_add() — add frontend/backend/ios, validates --framework enum
│   ├── upgrade.py      # run_upgrade() — diff-based updates, detects nextjs/rsbuild/kibo/vite
│   ├── generate.py     # generate_app subgroup — model, endpoint, component, page, hook, schema
│   ├── db.py           # db_app subgroup — migrate, makemigrations, status, seed, reset, shell, dump, load
│   ├── sync.py         # sync_app subgroup — types, zod, api-client, all (uses existing parsers)
│   ├── deps.py         # deps_app subgroup — check, update, audit
│   ├── health.py       # run_health() — Docker, DB, Redis, backend, frontend port/HTTP checks
│   ├── hooks.py        # hooks_app subgroup — install, status, run (pre-commit)
│   ├── workflow.py     # run_generate_workflow() — GitHub Actions / GitLab CI generation
│   ├── audit.py        # run_audit() — orchestrates 6 auditor classes + plugins
│   ├── dev.py          # run_dev() — start services with port conflict detection
│   ├── test.py         # run_test() — unified pytest + vitest with --parallel, timing
│   ├── lint.py         # run_lint() — unified ruff + eslint with --parallel, timing, --fix hint
│   ├── env.py          # run_env() — check/sync/show .env files
│   ├── rules.py        # run_rules() — generate CLAUDE.md, .cursorrules, GSD files
│   ├── context.py      # run_context() — dump project context as markdown/JSON
│   ├── client.py       # client_app subgroup — add/remove/install/run/dev/build/exec/which
│   ├── doctor.py       # run_doctor() — checks python, git, uv, bun, make, docker, ports
│   ├── info.py         # run_info() — presets, repos, examples tables
│   ├── version.py      # run_version() — version + PyPI update check
│   └── completions.py  # run_completions() — shell completion installer
│
├── generators/
│   ├── base.py         # BaseGenerator: create_root_directory, clone_and_strip, write_file
│   ├── fullstack.py    # FullstackGenerator: 8 steps (9 with iOS)
│   ├── backend_only.py # BackendOnlyGenerator: 6 steps
│   ├── frontend_only.py# FrontendOnlyGenerator: 5 steps
│   └── ios.py          # add_ios_to_project() + MyApp rename customization
│
├── auditors/
│   ├── base.py         # Severity, AuditType, AuditFinding, BaseAuditor, AuditReport
│   ├── types.py        # TypeSafetyAuditor — Pydantic ↔ TS/Zod field comparison
│   ├── quality.py      # CodeQualityAuditor — TODOs, stubs, mock data, debug, credentials
│   ├── endpoints.py    # EndpointAuditor — duplicate routes, missing auth, stubs, live probing
│   ├── tests.py        # CoverageAuditor — coverage gaps, naming, feature mapping
│   ├── dependencies.py # DependencyAuditor — unpinned, deprecated, duplicates
│   ├── vulnerabilities.py # VulnerabilityAuditor — CVE scanning (pip-audit, npm audit, OSV)
│   ├── report.py       # print_report(), print_json(), write_todo() (idempotent)
│   ├── html_report.py  # generate_html_report() — standalone HTML dashboard
│   └── plugins.py      # discover_plugins() — loads from mattstack-plugins/
│
├── parsers/
│   ├── python_schemas.py    # PydanticSchema/PydanticField, parse_pydantic_file()
│   ├── typescript_types.py  # TSInterface/TSField, parse_typescript_file()
│   ├── zod_schemas.py       # ZodSchema/ZodField, parse_zod_file()
│   ├── django_routes.py     # Route, parse_routes_file()
│   ├── nextjs_routes.py     # NextjsRoute, parse_nextjs_routes()
│   ├── test_files.py        # TestCase/TestSuite, parse_pytest_file(), parse_vitest_file()
│   └── dependencies.py      # Dependency/DependencyManifest, parse_pyproject_toml(), parse_package_json()
│
├── post_processors/    # customizer (rename), frontend_config (monorepo: vite/rsbuild/nextjs), b2b
├── templates/          # f-string functions: makefile, docker_compose, env, readme, gitignore,
│                       # claude_md, pre_commit_config, deploy configs (8 platforms)
└── utils/              # console, git, docker, process, yaml_config, package_manager
```

## Key Patterns

1. **Templates = Python functions** returning f-strings (not Jinja2). All in `templates/`.
2. **Generators inherit BaseGenerator (ABC)**. Each defines a `steps` property; base class runs them.
3. **ProjectConfig** is the single config object passed everywhere. Computed properties: `has_backend`, `has_frontend`, `is_fullstack`, `is_b2b`, `is_nextjs`, `backend_dir`, `frontend_dir`.
4. **FrontendFramework** enum: `react-vite`, `react-vite-starter`, `react-rsbuild`, `react-rsbuild-kibo`, `nextjs`.
5. **Parsers are pure functions** — regex-based, no AST, no new dependencies. Each returns dataclasses.
6. **Auditors inherit BaseAuditor**. Each has `run() → list[AuditFinding]`, uses `self.add_finding()`.
7. **Subgroups** (generate, db, sync, deps, hooks) use Typer subgroup pattern like `client_app`.
8. **Lazy imports** in `cli.py` — subgroups registered via `_register_subgroups()`, commands import on invoke.
9. **Timing output** on test, lint commands via `time.perf_counter()`.
10. **Port detection** in dev command via `check_port_available()` from `utils/process.py`.

## Common Workflows

### Add a new frontend framework
1. Add to `FrontendFramework` enum in `config.py`
2. Add repo URL to `REPO_URLS` in `config.py`
3. Add presets in `presets.py`
4. Add wizard choice in `commands/init.py`
5. Add upgrade detection in `commands/upgrade.py`
6. Add monorepo proxy in `post_processors/frontend_config.py`
7. Update templates: `root_readme.py`, `root_claude_md.py`
8. Update CLI help in `cli.py`
9. Update test in `tests/test_presets.py`

### Add a new audit domain
1. Create `parsers/new_parser.py` with parse function + find function
2. Create `auditors/new_auditor.py` inheriting `BaseAuditor`
3. Add to `AUDITOR_CLASSES` dict in `commands/audit.py`
4. Add to `AuditType` enum in `auditors/base.py`

### Add a new preset
1. Add to `PRESETS` dict in `presets.py`
2. No other changes needed — init command auto-discovers presets

### Add a new command subgroup
1. Create `commands/new_cmd.py` with `new_app = typer.Typer(...)` + subcommand functions
2. Register in `cli.py` `_register_subgroups()`: `app.add_typer(new_app, name="new")`

## Dev Commands

```bash
uv sync --extra dev            # Install with dev deps
uv run pytest -x -q            # Tests (596 tests)
uv run ruff check src/ tests/  # Lint
uv run ruff format src/ tests/ # Format
uv run mattstack init test --preset starter-fullstack -o /tmp  # E2E test
uv run mattstack audit /tmp/test  # E2E audit test
```

## Rules
- `uv` only (never pip/poetry)
- `bun` for JS (never npm/yarn)
- Type hints on every function
- No new dependencies — stdlib + typer/rich/questionary/pyyaml only
- Parsers use regex, not AST libs
- All auditors must produce `AuditFinding` objects
- Tests go in `tests/` mirroring `src/` structure
