# Boilerplate Consolidation — Design

Date: 2026-08-12
Status: Accepted
Scope: "Consolidation + monorepo hardening" (next tagged release)

## Problem

`FullstackGenerator` clones the backend boilerplate into `backend/` and the frontend
boilerplate into `frontend/`, then writes consolidated root files (`Makefile`,
`docker-compose.yml`, `.env`, `README.md`, `CLAUDE.md`, …). But `clone_and_strip` only
removes `.git` history and the django `cli/` dir. Each boilerplate's own standalone
root files survive, so a generated project ends up with **duplicate** `Makefile`,
`docker-compose*.yml`, and `.env*` files in `backend/`, `frontend/`, *and* the root —
two independent codebases glued together rather than one consolidated monorepo.

## Goals

1. One `Makefile`, one `.env` family, one `docker-compose` family at the root.
2. No standalone-project artifacts left inside `backend/` / `frontend/`.
3. Adopt durable patterns from the built-out reference apps (music-app, lfts-app):
   docker-compose profiles, multi-environment env templates, Dockerfiles under `docker/`.

## Non-goals

- Do not rename the service directories (stays `backend/` + `frontend/`).
- Do not modify the boilerplate repos themselves; they must still work standalone.
- Do not pull in the reference apps' full deploy/monitoring/backup surface (out of scope).

## Design

### 1. Consolidation step (new)

New post-processor `consolidate_monorepo(config)` in
`src/mattstack/post_processors/consolidate.py`, invoked from `FullstackGenerator` after
both clones and before root-file generation. It deletes standalone-project artifacts,
tolerating absence (defensive removal so an unexpected file is never fatal).

Remove from **backend/**:

- files: `Makefile`, `docker-compose*.yml`, `docker-compose*.yaml`, `Dockerfile*`,
  `.env*`, `README*`, `CLAUDE.md`, `.cursorrules`, `.gitignore`, `.dockerignore`,
  `.pre-commit-config.yaml`, `CHANGELOG.md`
- dirs: `cli/`, `docker/`, `deploy/`, `nginx/`, `env/`, `media/`, `files/`, and
  editor/agent dirs (`.claude/`, `.cursor/`, `.vscode/`, `.omp/`, `.agents/`,
  `.continue/`, `.kiro/`, `.windsurf/`, `.tanstack/`)

Remove from **frontend/**:

- files: `Makefile`, `docker-compose*.yml`, `docker-compose*.yaml`, `Dockerfile*`,
  `.env*`, `env.example`, `env.monorepo.example`, `README*`, `CLAUDE.md`, `.gitignore`,
  `.dockerignore`, `DEPLOYMENT.md`, `nginx.conf`
- dirs: `nginx/`, `docs/`, `dist/`, and editor/agent dirs (as above)

Keep (per-subpackage config, not duplicates): backend `pyproject.toml`, `manage.py`,
`api/`, `core/`, `billing/`, `conftest.py`, etc.; frontend `package.json`,
`bun.lock`, `eslint.config.js`, `.prettierrc`, `tsconfig*.json`, `vite.config.ts` /
`rsbuild.config.ts`, `tailwind.config.js`, `postcss.config.js`, `src/`, `index.html`,
`public/`, `vitest.config.ts`.

### 2. Root consolidated files (hardened)

- `Makefile` — single root; gains `--profile`/`--env-file` wiring (see §4–5).
- `docker-compose.yml` (dev) + `docker-compose.prod.yml` (prod).
- `.env.example` (dev reference) + `.env.production.example` (prod reference), both
  committed; `.env` and `.env.production` copied at generate time and gitignored.
- `README.md`, `CLAUDE.md`, `.cursorrules`, root `.gitignore` (updated to ignore the
  new env files), root `.dockerignore` (limits build context), `.pre-commit-config.yaml`,
  `tasks/todo.md`.

### 3. Dockerfiles generated from templates

mattstack-cli generates `docker/backend/Dockerfile` and `docker/frontend/Dockerfile`
from framework-aware templates (django-ninja / fastapi / django-matt / nestjs for
backend; vite / rsbuild / nextjs for frontend). Build context is the repo root;
the root `.dockerignore` excludes `.git`, `**/node_modules`, `**/.venv`,
`**/__pycache__`, `**/dist`, and the non-target service tree. Compose `build` blocks
use `context: .` + `dockerfile: docker/<service>/Dockerfile`.

### 4. Docker profiles

`docker-compose.yml` tags optional services under a `celery` profile (worker + beat).
Makefile targets:

- `make up` → `docker compose up -d` (db, redis, api-dev, frontend-dev)
- `make up-celery` → `docker compose --profile celery up -d`
- `make up-prod` → `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`
- `make logs` / `make down` with matching profile flags

### 5. Multi-env

- `make up` uses `.env` (dev defaults).
- `make up-prod` uses `--env-file .env.production`.

### 6. Verification

- New unit tests in `tests/test_post_processors/test_consolidate.py`: each standalone
  file/dir is removed, kept files survive, absent files tolerated.
- Generator integration test: a fullstack generate produces a single root `Makefile`,
  no `backend/Makefile` or `frontend/Makefile`, relocated Dockerfiles exist, env
  templates + gitignored copies exist, compose references the relocated Dockerfiles.
- Existing generator/preset tests updated for any new root-file expectations.
- Smoke test: run `mattstack generate` on a django-ninja + react-vite fullstack and
  `docker compose config` to confirm valid compose.

## Reference apps consulted

- `~/dev/music-app/music-app` (`music-django/` + `music-rsbuild/`): docker profiles,
  db dump/fast-reset, gauntlet, OpenAPI type-sync, deploy pipeline.
- `~/dev/lfts-app/lfts-app` (`lfts-django/` + `lfts-spa/`): docker profiles
  (dev/dev-docker/server/prod), multi-env templates, `docker/<service>/Dockerfile`
  with `context: ./<service>` + `dockerfile: ../docker/<service>/Dockerfile`.
- `~/dev/music-education/web-app` (`backend/` + `frontend/`): `.env`, `.env.production`,
  `.env.production.example`, root `scripts/` deploy helpers.
