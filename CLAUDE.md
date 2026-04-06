# mattstack

CLI to scaffold fullstack monorepos, generate components, sync types, and audit for quality.

## Stack
- Python 3.12+, uv (never pip), ruff, hatchling, Apache-2.0
- 26 commands, 6 subgroups, 12 presets, 7 source repos

## Dev
```bash
uv sync --extra dev            # Install
uv run pytest -x -q            # 596 tests
uv run ruff check src/ tests/  # Lint
```

## Commands
```bash
mattstack init my-app -p starter-fullstack   # Scaffold project
mattstack add frontend -f react-rsbuild-kibo # Add component
mattstack generate model Product --fields "title:str price:decimal"
mattstack generate component ProductCard --with-test
mattstack db migrate | seed | reset          # Database ops
mattstack sync types | zod | api-client      # Pydantic → TS/Zod
mattstack dev                                # Start all services
mattstack test --parallel                    # Run tests
mattstack lint --parallel --fix              # Lint + fix
mattstack fmt                                # Format all
mattstack audit --html                       # Static analysis
mattstack deps check | update | audit        # Dependencies
mattstack health --live                      # Service health
mattstack hooks install                      # Git hooks
mattstack workflow                           # Generate CI/CD
mattstack info                               # Show presets/repos
```

## Presets
starter-fullstack, b2b-fullstack, starter-api, b2b-api, starter-frontend, simple-frontend, rsbuild-fullstack, rsbuild-frontend, kibo-fullstack, kibo-frontend, nextjs-fullstack, nextjs-frontend

## Frameworks
`react-vite` | `react-vite-starter` | `react-rsbuild` | `react-rsbuild-kibo` | `nextjs`

## Rules
- `uv` only (never pip/poetry), `bun` for JS (never npm/yarn)
- Type hints on every function, no new dependencies
- Parsers use regex (not AST), auditors produce `AuditFinding` objects
- Tests in `tests/` mirroring `src/` structure

## Architecture
See [docs/architecture.md](docs/architecture.md) for file map, patterns, and extension workflows.
