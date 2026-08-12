# Boilerplate Consolidation — Implementation Plan

> **Goal:** Generate fullstack/backend-only/frontend-only monorepos with a single consolidated `Makefile`/`.env`/`docker-compose` at the root and no standalone-project artifacts inside `backend/`/`frontend/`.

**Architecture:** A new `consolidate` post-processor strips standalone-project files from cloned subdirectories; `docker/backend/Dockerfile` + `docker/frontend/Dockerfile` are generated from framework-aware templates; compose/env/makefile templates are hardened with profiles and multi-env support.

**Tech Stack:** Python 3.12, pytest (TDD), ruff, mypy strict.

**Design:** `docs/plans/2026-08-12-boilerplate-consolidation-design.md`

---

## Task 1 — Consolidation post-processor

**Files:**
- Create: `src/mattstack/post_processors/consolidate.py`
- Test: `tests/test_post_processors/test_consolidate.py` (new dir)

Implement `consolidate_backend(config)` and `consolidate_frontend(config)`, each deleting the standalone file/dir lists from the design, tolerating absence. Keep `pyproject.toml`, `manage.py`, `api/`, `core/` (backend); `package.json`, `src/`, `tsconfig*.json`, tooling configs (frontend).

## Task 2 — Dockerfile templates

**Files:**
- Create: `src/mattstack/templates/dockerfiles.py`
- Test: `tests/test_templates/test_dockerfiles.py`

`generate_backend_dockerfile(config)` (django-ninja/fastapi/django-matt/nestjs) and `generate_frontend_dockerfile(config)` (vite/rsbuild/nextjs). Build context = repo root; each `COPY backend/…` / `COPY frontend/…`.

## Task 3 — Wire into generators

**Files:**
- Modify: `src/mattstack/generators/fullstack.py`, `backend_only.py`, `frontend_only.py`
- Test: `tests/test_generators/test_fullstack.py`, `test_backend_only.py`, `test_frontend_only.py`

After cloning (and before/after root files as appropriate): call the consolidate functions and write `docker/<service>/Dockerfile`.

## Task 4 — Compose templates (relocated Dockerfiles + celery profile)

**Files:**
- Modify: `src/mattstack/templates/docker_compose.py`, `docker_compose_prod.py`
- Test: `tests/test_templates/test_docker_compose.py` (existing? verify)

Dev compose: `build: { context: ., dockerfile: docker/backend/Dockerfile }` (frontend `docker/frontend/Dockerfile` or `.dev`), celery worker/beat tagged `profiles: ["celery"]`. Prod compose references relocated Dockerfiles.

## Task 5 — Env templates + gitignore

**Files:**
- Modify: `src/mattstack/templates/root_env.py`, `root_gitignore.py`
- Test: `tests/test_commands/test_env.py`

Add `generate_env_production_example(config)`; generators write `.env.example`, `.env.production.example` and gitignored `.env`, `.env.production`; gitignore gains `.env.production`.

## Task 6 — Makefile profiles + env-file wiring

**Files:**
- Modify: `src/mattstack/templates/root_makefile.py`
- Test: `tests/test_commands/test_dev.py` / a makefile test

Add `up-celery` (`--profile celery`), `up-prod` (`-f docker-compose.prod.yml --env-file .env.production`), and `--env-file`/profile flags on `up`/`logs`/`down`.

## Task 7 — End-to-end smoke test + release

Generate a real django-ninja + react-vite fullstack (or use mocks) and run `docker compose config` to validate. Bump version to `0.7.0`, update changelog/docs, tag `v0.7.0`.
