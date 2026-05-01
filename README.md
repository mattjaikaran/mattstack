# mattstack

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-749%20passing-brightgreen.svg)](#development)

CLI to scaffold fullstack monorepos from battle-tested boilerplates, then audit them for quality.

Skip the week of project setup — `mattstack init` clones production-ready Django Ninja + React boilerplates, wires them together, and hands you a running monorepo in under a minute. From there, `generate crud` scaffolds a complete full-stack feature (model → schema → controller → TypeScript client → React hooks → component) in a single command. The `audit` command then keeps the codebase honest: type drift between Pydantic and TypeScript, missing tests, stub endpoints, hardcoded credentials, and CVEs — all surfaced in one pass.

## Headline: Generate a Full-Stack Feature in Seconds

One command creates a complete vertical slice — backend model, Pydantic schemas, Django Ninja controller, TypeScript API client, TanStack Query hooks, and a React list component:

```bash
mattstack generate crud Product --fields "name:str price:decimal"
```

**Files created:**

```
backend/apps/products/models/product.py
backend/apps/products/schemas/product.py
backend/apps/products/api/product.py
backend/apps/products/admin/product_admin.py
frontend/src/api/product.ts
frontend/src/hooks/useProducts.ts
frontend/src/components/ProductList/index.tsx
```

**What's inside each file:**

`backend/apps/products/models/product.py`
```python
"""Django model for Product."""

from __future__ import annotations

from decimal import Decimal
from django.db import models
from core.models.base import AbstractBaseModel


class Product(AbstractBaseModel):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name
```

`backend/apps/products/schemas/product.py`
```python
"""Ninja schemas for Product."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ninja import Schema
from pydantic import ConfigDict


class ProductBaseSchema(Schema):
    name: str
    price: Decimal


class ProductCreateSchema(ProductBaseSchema):
    pass


class ProductUpdateSchema(ProductBaseSchema):
    name: str | None = None
    price: Decimal | None = None


class ProductResponseSchema(ProductBaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

`backend/apps/products/api/product.py`
```python
"""API controller for Product."""

from __future__ import annotations

from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja_extra import api_controller, http_delete, http_get, http_post, http_put

from apps.products.models.product import Product
from apps.products.schemas.product import (
    ProductCreateSchema,
    ProductResponseSchema,
    ProductUpdateSchema,
)
from core.auth import JWTAuth, OptionalJWTAuth
from core.controllers.base_controller import BaseController, handle_exceptions


@api_controller("/products", tags=["Product"])
class ProductController(BaseController):
    @http_get("/", response=list[ProductResponseSchema])
    @handle_exceptions()
    def list_products(self, request, search: str | None = None, limit: int = 20, offset: int = 0):
        """List Products with pagination."""
        qs = Product.objects.all()
        if search:
            qs = qs.filter(id__icontains=search)
        return qs[offset:offset + limit]

    @http_get("/{product_id}", response={200: ProductResponseSchema, 404: dict}, auth=OptionalJWTAuth())
    @handle_exceptions()
    def get_product(self, request, product_id: UUID):
        """Get a single Product."""
        return get_object_or_404(Product, id=product_id)

    @http_post("/", response={201: ProductResponseSchema, 400: dict}, auth=JWTAuth())
    @handle_exceptions(success_status=201)
    def create_product(self, request, payload: ProductCreateSchema):
        """Create a new Product."""
        obj = Product.objects.create(**payload.model_dump())
        return obj

    @http_put("/{product_id}", response={200: ProductResponseSchema, 403: dict}, auth=JWTAuth())
    @handle_exceptions()
    def update_product(self, request, product_id: UUID, payload: ProductUpdateSchema):
        """Update a Product."""
        obj = get_object_or_404(Product, id=product_id)
        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(obj, attr, value)
        obj.save()
        return obj

    @http_delete("/{product_id}", response={204: None}, auth=JWTAuth())
    @handle_exceptions()
    def delete_product(self, request, product_id: UUID):
        """Delete a Product."""
        obj = get_object_or_404(Product, id=product_id)
        obj.delete()
        return 204, None
```

`frontend/src/api/product.ts`
```typescript
// Auto-generated by mattstack generate crud

export interface Product {
  id: string;
  name: string;
  price: number;
  createdAt: string;
  updatedAt: string;
}

export interface ProductCreate {
  name: string;
  price: number;
}

export interface ProductUpdate {
  name?: string;
  price?: number;
}

const BASE_URL = "http://localhost:8000";

export async function listProducts(page = 1, pageSize = 20): Promise<Product[]> {
  const offset = (page - 1) * pageSize;
  const res = await fetch(`${BASE_URL}/products/?limit=${pageSize}&offset=${offset}`);
  if (!res.ok) throw new Error(`Failed to list products: ${res.statusText}`);
  return res.json();
}

export async function getProduct(id: string): Promise<Product> {
  const res = await fetch(`${BASE_URL}/products/${id}`);
  if (!res.ok) throw new Error(`Failed to get product: ${res.statusText}`);
  return res.json();
}

export async function createProduct(data: ProductCreate): Promise<Product> {
  const res = await fetch(`${BASE_URL}/products/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create product: ${res.statusText}`);
  return res.json();
}

export async function updateProduct(id: string, data: ProductUpdate): Promise<Product> {
  const res = await fetch(`${BASE_URL}/products/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update product: ${res.statusText}`);
  return res.json();
}

export async function deleteProduct(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/products/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete product: ${res.statusText}`);
}
```

`frontend/src/hooks/useProducts.ts`
```typescript
// Auto-generated by mattstack generate crud
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listProducts,
  getProduct,
  createProduct,
  updateProduct,
  deleteProduct,
} from "@/api/product";
import type { ProductCreate, ProductUpdate } from "@/api/product";

export function useProductList(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["products", page, pageSize],
    queryFn: () => listProducts(page, pageSize),
    placeholderData: (prev) => prev,
  });
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ["products", id],
    queryFn: () => getProduct(id),
    enabled: !!id,
  });
}

export function useCreateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProductCreate) => createProduct(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProductUpdate }) =>
      updateProduct(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useDeleteProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProduct(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
```

Add `--with-tests` to also generate pytest API tests and a Vitest component test.

### `generate crud` Options

| Flag | Description |
|------|-------------|
| `--fields, -f` | Field definitions: `name:type` (str, int, decimal, bool, date, datetime, text, email, url, uuid, fk) |
| `--app, -a` | Django app name (default: auto-detect) |
| `--path, -p` | Project root path |
| `--with-tests` | Also generate pytest + Vitest tests |
| `--dry-run` | Preview without creating files |

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
| `mattstack create [name]` | Alias for `init` |
| `mattstack add <component>` | Add frontend/backend/ios to existing project |
| `mattstack upgrade` | Pull latest boilerplate changes into project |
| `mattstack generate <type>` | Scaffold models, endpoints, components, pages, hooks |
| `mattstack db <action>` | Database management (migrate, seed, reset, status) |
| `mattstack sync <target>` | Generate TS types, Zod schemas, API hooks from Pydantic |
| `mattstack audit [path]` | Run static analysis on a generated project |
| `mattstack dev` | Start all development services (docker, backend, frontend) |
| `mattstack test` | Run tests across backend and frontend |
| `mattstack lint` | Run linters across backend and frontend |
| `mattstack fmt` | Format all code (lint --fix --format-check) |
| `mattstack deps <action>` | Check outdated, update, and audit dependencies |
| `mattstack health` | Check health of all services (Docker, DB, Redis, servers) |
| `mattstack hooks <action>` | Install, check status, and run git hooks |
| `mattstack workflow` | Generate CI/CD workflows (GitHub Actions, GitLab CI) |
| `mattstack env [action]` | Manage environment variables (.env files) |
| `mattstack doctor` | Check your development environment |
| `mattstack info` | Show available presets and source repos |
| `mattstack presets` | List available presets (alias for info) |
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
| `--format, -f` | Output format: `markdown` (default), `json`, `claude` |
| `--output, -o` | Write context to a file |

```bash
# Dump project context for AI agents
mattstack context

# Claude-optimized format
mattstack context --format claude

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

### `generate` Subcommands

```bash
# Full-stack CRUD feature (model + schema + controller + admin + frontend)
mattstack generate crud Product --fields "name:str price:decimal"

# Add tests alongside
mattstack generate crud Product --fields "name:str price:decimal" --with-tests

# Django model + Pydantic schema + API router
mattstack generate model Product --fields "title:str price:decimal description:text is_active:bool"

# Django Ninja endpoint
mattstack generate endpoint /products --method GET --auth

# React component with test
mattstack generate component ProductCard --with-test

# TanStack Router page
mattstack generate page dashboard

# React hook
mattstack generate hook useProducts

# Pydantic schema only (no model)
mattstack generate schema ProductCreate --fields "title:str price:decimal"
```

### `db` Subcommands

```bash
mattstack db migrate           # Run Django migrations
mattstack db makemigrations    # Create migrations
mattstack db status            # Show migration status
mattstack db seed              # Seed from backend/seed.py
mattstack db seed --fresh      # Flush + migrate + seed
mattstack db reset             # Flush + migrate (interactive confirm)
mattstack db reset --seed      # Reset and seed
mattstack db shell             # Django dbshell
mattstack db dump --app users  # Dump fixtures
mattstack db load fixtures.json
```

### `sync` Subcommands

```bash
# Generate TypeScript interfaces from Pydantic models
mattstack sync types

# Generate Zod validation schemas
mattstack sync zod

# Generate TanStack Query hooks from Django routes
mattstack sync api-client

# Run all three
mattstack sync all
```

### `deps` Subcommands

```bash
mattstack deps check           # Show outdated packages
mattstack deps update          # Update both stacks
mattstack deps update --backend-only
mattstack deps audit           # Security vulnerability scan
```

### `health`

```bash
mattstack health               # Check Docker, DB, Redis ports
mattstack health --live        # Also probe HTTP endpoints
```

### `hooks`

```bash
mattstack hooks install        # Install pre-commit hooks
mattstack hooks status         # Show hook status
mattstack hooks run            # Run all hooks manually
```

### `workflow`

```bash
mattstack workflow                          # GitHub Actions (default)
mattstack workflow --platform gitlab-ci     # GitLab CI
mattstack workflow --dry-run                # Preview without writing
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
| `kibo-fullstack` | fullstack | Django Ninja + React Rsbuild + Kibo UI |
| `kibo-frontend` | frontend-only | React Rsbuild + Kibo UI (dashboards, kanban) |
| `nextjs-fullstack` | fullstack | Django Ninja + Next.js (App Router) |
| `nextjs-frontend` | frontend-only | Next.js standalone (App Router, Tailwind) |

## AI Agent Integration

`mattstack context` dumps a structured snapshot of your project — routes, models, schemas, test coverage, env vars — formatted for AI assistants.

```bash
# Generate Claude-optimized context and pipe directly into Claude Code
mattstack context --format claude | claude --print "Review my API surface"

# Write to file for use in your editor's AI sidebar
mattstack context --format claude -o context.md

# JSON format for programmatic use
mattstack context --format json | jq '.endpoints[]'
```

The `claude` format includes:
- All discovered Django Ninja routes with method, path, auth, and response types
- Pydantic schemas mapped to their TypeScript counterparts (with drift detection)
- Test coverage gaps by feature area
- Outstanding audit findings from `tasks/todo.md`

This lets you ask an AI assistant "what endpoints are missing auth?" or "generate the missing frontend types for these schemas" with full project awareness — no manual copy-paste.

## Comparison

| | mattstack | cookiecutter-django | django-startproject | Manual setup |
|---|---|---|---|---|
| **Setup time** | < 1 min | 5–10 min | 10–30 min | Days |
| **Full-stack** | Django + React in one command | Django only | Django only | Each stack separately |
| **Feature generation** | `generate crud` scaffolds 7 files | None | None | Write by hand |
| **Type safety** | Pydantic → TypeScript sync built-in | None | None | Manual |
| **Audit** | Static analysis, CVE scanning, type drift | None | None | Third-party tools |
| **AI context** | `context --format claude` | None | None | None |
| **Presets** | 12 (fullstack, B2B, frontend, Next.js) | 1 | 1 | N/A |
| **Post-setup** | `generate`, `sync`, `audit`, `dev`, `test`, `lint` all work | Cookiecutter only | None | Wire it yourself |

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
| `react-rsbuild-kibo` | [react-rsbuild-kibo-boilerplate](https://github.com/mattjaikaran/react-rsbuild-kibo-boilerplate) |
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

## Roadmap: django-matt + Mateus

First-class support for [django-matt](https://github.com/mattjaikaran/django-matt) and [mateus](https://github.com/mattjaikaran/mateus) is planned across three phases:

| Phase | What | Status |
|-------|------|--------|
| **15A** | django-matt backend support — `BackendFramework` enum, `django-matt-boilerplate` repo, updated generators/parsers/type sync | Unblocked (django-matt v0.9.0 on PyPI) |
| **15B** | Mateus frontend support — `FrontendFramework.REACT_MATEUS`, `react-mateus-boilerplate` repo, mateus as package manager/dev server/test runner/linter | Blocked (mateus not yet published) |
| **15C** | `matt-fullstack` preset — django-matt + React SSR via mateus, dockerized with Postgres + Redis + Celery | Blocked on 15A + 15B |

### Upcoming Presets

| Preset | Type | Description |
|--------|------|-------------|
| `matt-api` | backend-only | django-matt API (replaces django-ninja ecosystem) |
| `matt-fullstack` | fullstack | django-matt + React Mateus (SSR) |
| `matt-b2b-fullstack` | fullstack | django-matt B2B + React Mateus (SSR) |
| `mateus-fullstack` | fullstack | Django Ninja + React Mateus |
| `mateus-frontend` | frontend-only | React Mateus standalone |

### What Changes

- **Backend**: `django-matt` replaces `django-ninja` + `django-ninja-extra` + `django-ninja-jwt` as a single meta-framework (54+ modules, JWT/OAuth/WebSockets/billing built-in)
- **Frontend**: `mateus` replaces `bun` + `vite` as a single Rust binary (runtime, bundler, test runner, linter, package manager, SSR engine)
- **Type sync**: django-matt has built-in `sync_types` CLI — mattstack wraps or delegates to it
- **Generators**: `generate model` outputs django-matt controllers + `CRUDService` instead of ninja routers
- **Audit**: endpoint auditor recognizes django-matt controller decorators (`@get`, `@post` on `APIController`)
- **Client commands**: `mateus install`, `mateus add`, `mateus dev`, `mateus test`, `mateus lint`, `mateus fmt`

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
uv run pytest -x -q            # Run tests (749 tests)
uv run pytest --cov            # With coverage
uv run ruff check src/ tests/  # Lint
uv run ruff format src/ tests/ # Format
```

## License

Apache-2.0
