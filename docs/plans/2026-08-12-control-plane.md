# Control Plane & Pluggable Integrations — Implementation Plan

> **Goal:** Wire a deterministic control plane into mattstack-cli (settings-driven strictness, branch protection, pluggable board/notify backends, task SSOT) plus anti-slop gates, secret hardening, and harness-agnostic rules — across mattstack-cli, the boilerplates, homelab, and project-mgmt.

**Architecture:** One `mattstack.yml` config file drives strictness and branch protection; a `BoardBackend` protocol abstracts the kanban (Axis / Hermes / Linear / Jira / none); a `notify` module abstracts deploy notifications (Hermes/Telegram/webhook). Boilerplate changes are additive gates only.

**Tech Stack:** Python 3.12 (mattstack-cli), uv, pytest (TDD), ruff, mypy strict. Design: `docs/plans/2026-08-12-control-plane-design.md`.

**Non-goals:** no swarm orchestrator, no kanban rebuild, no Telegram bot, no conflict with `boilerplate-consolidation` (separate v0.7.0).

---

## Phase 0 — Secret hardening (independent)

**Files:**
- Modify: `~/dev/homelab/scripts/populate-tasks.py:14-20`, `~/dev/homelab/scripts/recalibrate-axis.py:14-20`
- Delete/gitignore: `~/dev/project-mgmt/cookies.txt`, committed `.env` / `.env.development`

Replace the hardcoded PostgreSQL password + bare IP with `os.environ` reads (`AXIS_DB_USER`, `AXIS_DB_PASSWORD`, `AXIS_DB_HOST`, `AXIS_DB_PORT`, `AXIS_DB_NAME`), falling back to a non-committed `.env`. Non-destructive: never commit new secrets, emit `.env.example` placeholders.

## Phase 1 — `mattstack.yml` config loader (foundation)

**Files:**
- Create: `src/mattstack/config_file.py`
- Modify: `src/mattstack/commands/init.py` (write `mattstack.yml` template)
- Test: `tests/test_config_file.py`

`MattstackConfig` dataclass + `load_config(path) -> MattstackConfig` with schema defaults from the design doc §1. Loader uses the existing `utils/yaml_config.py` pattern.

## Phase 2 — `mattstack protect` (branch protection)

**Files:**
- Create: `src/mattstack/commands/protect.py`
- Modify: `src/mattstack/commands/hooks.py` (or register in cli.py)
- Test: `tests/test_commands/test_protect.py`

When `protect_main: true`: enable `no-commit-to-branch` in `.pre-commit-config.yaml`, write `CODEOWNERS`, apply GitHub ruleset via `gh api repos/{owner}/{repo}/rulesets`.

## Phase 3 — `mattstack board` (pluggable kanban)

**Files:**
- Create: `src/mattstack/boards/base.py`, `boards/axis.py`, `boards/none.py`
- Create (later): `boards/linear.py`, `boards/jira.py`, `boards/hermes.py`
- Create: `src/mattstack/commands/board.py`
- Test: `tests/test_boards/test_axis.py`

`BoardBackend` protocol + `AxisBackend` wrapping the Axis endpoints in the design doc §2. `mattstack board <create|list|claim|transition|link-pr|sync>`.

## Phase 4 — `mattstack todo` + task SSOT

**Files:**
- Create: `src/mattstack/commands/todo.py`
- Test: `tests/test_commands/test_todo.py`

`todo move <item>` moves `tasks/todo.md → tasks/completed.md` (date + commit SHA). `board sync` pushes `todo.md` into the configured backend.

## Phase 5 — `mattstack notify` + deploy wiring

**Files:**
- Create: `src/mattstack/notify.py`, `src/mattstack/commands/notify.py`
- Modify: `~/dev/django-ninja-boilerplate/scripts/deploy.sh` (add `notify_deploy` at end of provider `case`)
- Test: `tests/test_notify.py`

Backends `hermes` | `telegram` | `webhook` | `none`, POSTing the deploy envelope from the design doc §4.

## Phase 6 — Dependency + scope gates

**Files:**
- Create: `~/dev/django-ninja-boilerplate/scripts/check_dependencies.py`
- Create: `~/dev/react-vite-boilerplate/scripts/check_dependencies.ts`
- Modify: gauntlet registration (both stacks)
- Modify: `src/mattstack/commands/verify.py` (scope enforcement)

Fail if manifest changed without `DEPENDENCIES.md` entry; `verify --scope` fails on out-of-scope edits.

## Phase 7 — React convention parity (independent)

**Files:**
- Modify: `~/dev/react-vite-boilerplate/scripts/check_conventions.ts`
- Modify (mirror): `~/dev/boilerplates/react-rsbuild-boilerplate`, `react-rsbuild-kibo-boilerplate`

Add `NO_USE_STATE_FOR_FORMS` (react-hook-form + zod), `NO_INLINE_FETCH` (API calls in hooks/lib), `COMPONENT_SIZE` (200 lines).

## Phase 8 — `mattstack rules sync` (harness-agnostic)

**Files:**
- Modify: `src/mattstack/commands/rules.py`
- Test: `tests/test_commands/test_rules.py`

Regenerate `.claude/`, `.cursor/`, `.windsurf/`, `.kiro/`, `.continue/`, `.agents/` adapters from canonical `.omp/` + `.context/`.

---

## Dependency graph

```
Phase 0 ── (independent)
Phase 7 ── (independent)
Phase 1 ──> 2 ──> (done)
        └──> 3 ──> 4
        └──> 5
        └──> 6
        └──> 8
```

## Open questions (block Phases 3, 5)

1. What is "Hermes' kanban" — Axis itself, a separate homelab board, or `tasks/todo.md`?
2. Linear/Jira: export-only (recommended) or two-way sync?
3. Deploy notify channel: Hermes→Telegram (recommended) or direct Telegram bot?
