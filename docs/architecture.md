# mattstack Architecture

## File Map

```
src/mattstack/
├── cli.py              # Typer app — 26 commands, 6 subgroups
├── config.py           # ProjectType, Variant, FrontendFramework (5), DeploymentTarget enums
│                       # ProjectConfig dataclass, REPO_URLS (7 repos)
├── presets.py          # 12 presets (starter/b2b × fullstack/api/frontend, rsbuild, kibo, nextjs)
│
├── commands/
│   ├── init.py         # 3 modes: config-file → preset → interactive wizard
│   ├── add.py          # Add frontend/backend/ios, validates --framework
│   ├── upgrade.py      # Diff-based updates, detects nextjs/rsbuild/kibo/vite
│   ├── generate.py     # Subgroup: model, endpoint, component, page, hook, schema
│   ├── db.py           # Subgroup: migrate, makemigrations, status, seed, reset, shell, dump, load
│   ├── sync.py         # Subgroup: types, zod, api-client, all (uses existing parsers)
│   ├── deps.py         # Subgroup: check, update, audit
│   ├── health.py       # Docker, DB, Redis, backend, frontend port/HTTP checks
│   ├── hooks.py        # Subgroup: install, status, run (pre-commit)
│   ├── workflow.py     # GitHub Actions / GitLab CI generation
│   ├── audit.py        # 6 auditor classes + plugin loader
│   ├── dev.py          # Start services with port conflict detection
│   ├── test.py         # Unified pytest + vitest, --parallel, timing
│   ├── lint.py         # Unified ruff + eslint, --parallel, timing
│   ├── env.py          # check/sync/show .env files
│   ├── rules.py        # Generate CLAUDE.md, .cursorrules, GSD files
│   ├── context.py      # Dump project context as markdown/JSON
│   ├── client.py       # Subgroup: add/remove/install/run/dev/build/exec/which
│   ├── doctor.py       # Environment checks
│   ├── info.py         # Presets, repos, examples tables
│   ├── version.py      # Version + update check
│   └── completions.py  # Shell completions
│
├── generators/         # BaseGenerator ABC → Fullstack/BackendOnly/FrontendOnly + iOS
├── auditors/           # BaseAuditor ABC → types, quality, endpoints, tests, dependencies, vulnerabilities
├── parsers/            # Pure regex parsers: pydantic, typescript, zod, django_routes, nextjs, tests, deps
├── post_processors/    # customizer, frontend_config (vite/rsbuild/kibo/nextjs monorepo), b2b
├── templates/          # f-string template functions (makefile, docker_compose, env, readme, etc.)
└── utils/              # console, git, docker, process, yaml_config, package_manager
```

## Key Patterns

1. **Templates = Python functions** returning f-strings (not Jinja2)
2. **Generators inherit BaseGenerator**. Each defines `steps` property; base runs them
3. **ProjectConfig** is the single config object. Properties: `has_backend`, `has_frontend`, `is_fullstack`, `is_b2b`, `is_nextjs`
4. **FrontendFramework** enum: react-vite, react-vite-starter, react-rsbuild, react-rsbuild-kibo, nextjs
5. **Parsers are pure functions** — regex-based, no AST, no deps. Return dataclasses
6. **Auditors inherit BaseAuditor**. `run() → list[AuditFinding]`
7. **Subgroups** use Typer pattern: `new_app = typer.Typer()`, registered in `_register_subgroups()`
8. **Lazy imports** in cli.py — each command imports its module only when invoked

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
1. Create `parsers/new_parser.py`
2. Create `auditors/new_auditor.py` inheriting `BaseAuditor`
3. Add to `AUDITOR_CLASSES` in `commands/audit.py`
4. Add to `AuditType` enum in `auditors/base.py`

### Add a new command subgroup
1. Create `commands/new_cmd.py` with `new_app = typer.Typer(...)` + subcommands
2. Register in `cli.py` `_register_subgroups()`
