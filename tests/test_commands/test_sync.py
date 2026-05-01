"""Tests for sync api-client — Phase 19: mutations, pagination, ApiError, --base-url."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from mattstack.commands.sync import (
    API_ERROR_INTERFACE,
    _infer_response_type,
    _pascal_to_snake,
    _route_to_hooks,
    _snake_to_camel,
)
from mattstack.parsers.django_routes import Route


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _route(method: str, path: str, func: str, is_stub: bool = False) -> Route:
    return Route(
        method=method,
        path=path,
        function_name=func,
        file=Path("api.py"),
        line=1,
        is_stub=is_stub,
    )


# ---------------------------------------------------------------------------
# _pascal_to_snake
# ---------------------------------------------------------------------------


def test_pascal_to_snake_simple() -> None:
    assert _pascal_to_snake("Product") == "product"


def test_pascal_to_snake_compound() -> None:
    assert _pascal_to_snake("OrderItem") == "order_item"


def test_pascal_to_snake_all_upper() -> None:
    assert _pascal_to_snake("User") == "user"


# ---------------------------------------------------------------------------
# GET hooks — basic and paginated
# ---------------------------------------------------------------------------


def test_get_hook_basic() -> None:
    route = _route("GET", "/api/products/{id}", "get_product")
    hooks = _route_to_hooks(route, {"Product"})
    assert len(hooks) == 1
    hook = hooks[0]
    assert "useGetProduct" in hook
    assert "useQuery" in hook
    assert "id: string" in hook
    assert "queryKey: ['get_product', id]" in hook
    assert "apiClient.get<Product>" in hook


def test_get_list_hook_no_paginated_without_type() -> None:
    route = _route("GET", "/api/items/", "list_items")
    hooks = _route_to_hooks(route, set())
    # No known type → only one hook, no paginated variant
    assert len(hooks) == 1
    assert "useListItems" in hooks[0]


def test_get_list_hook_generates_paginated_variant() -> None:
    route = _route("GET", "/api/products/", "list_products")
    hooks = _route_to_hooks(route, {"Product"})
    assert len(hooks) == 2

    main_hook, paged_hook = hooks
    assert "useListProducts" in main_hook
    assert "useProductList" in paged_hook


def test_paginated_hook_signature() -> None:
    route = _route("GET", "/api/products/", "list_products")
    hooks = _route_to_hooks(route, {"Product"})
    paged = hooks[1]
    assert "page: number = 1" in paged
    assert "pageSize: number = 20" in paged
    assert "keepPreviousData" in paged
    assert "placeholderData: keepPreviousData" in paged


def test_paginated_hook_query_key() -> None:
    route = _route("GET", "/api/products/", "list_products")
    hooks = _route_to_hooks(route, {"Product"})
    paged = hooks[1]
    assert "queryKey: ['products', page, pageSize]" in paged


def test_paginated_hook_path_includes_page_params() -> None:
    route = _route("GET", "/api/products/", "list_products")
    hooks = _route_to_hooks(route, {"Product"})
    paged = hooks[1]
    assert "page=${page}" in paged
    assert "page_size=${pageSize}" in paged


# ---------------------------------------------------------------------------
# Mutation hooks — POST / PUT / PATCH / DELETE
# ---------------------------------------------------------------------------


def test_post_hook_generates_mutation() -> None:
    route = _route("POST", "/api/products/", "create_product")
    hooks = _route_to_hooks(route, {"Product"})
    assert len(hooks) == 1
    hook = hooks[0]
    assert "useMutation" in hook
    assert "useCreateProduct" in hook
    assert "useQueryClient" in hook


def test_post_hook_infers_create_schema_suffix() -> None:
    route = _route("POST", "/api/products/", "create_product")
    hooks = _route_to_hooks(route, {"Product", "ProductCreateSchema"})
    hook = hooks[0]
    assert "data: ProductCreateSchema" in hook


def test_post_hook_infers_update_schema_suffix() -> None:
    route = _route("PUT", "/api/products/{id}", "update_product")
    hooks = _route_to_hooks(route, {"Product", "ProductUpdateSchema"})
    hook = hooks[0]
    assert "data: ProductUpdateSchema" in hook


def test_post_hook_falls_back_to_create_suffix() -> None:
    route = _route("POST", "/api/products/", "create_product")
    hooks = _route_to_hooks(route, {"Product", "ProductCreate"})
    hook = hooks[0]
    assert "data: ProductCreate" in hook


def test_post_hook_uses_unknown_when_no_input_type() -> None:
    route = _route("POST", "/api/products/", "create_product")
    hooks = _route_to_hooks(route, {"Product"})
    hook = hooks[0]
    assert "data: unknown" in hook


def test_post_hook_has_on_success_invalidate() -> None:
    route = _route("POST", "/api/products/", "create_product")
    hooks = _route_to_hooks(route, {"Product"})
    hook = hooks[0]
    assert "onSuccess" in hook
    assert "invalidateQueries" in hook
    assert "'products'" in hook


def test_put_hook_invalidates_resource() -> None:
    route = _route("PUT", "/api/order-items/{id}", "update_order_item")
    hooks = _route_to_hooks(route, {"OrderItem"})
    hook = hooks[0]
    assert "invalidateQueries" in hook
    assert "'order_items'" in hook


def test_delete_hook_generates_mutation() -> None:
    route = _route("DELETE", "/api/products/{id}", "delete_product")
    hooks = _route_to_hooks(route, {"Product"})
    assert len(hooks) == 1
    hook = hooks[0]
    assert "useMutation" in hook
    assert "useDeleteProduct" in hook
    assert "apiClient.delete" in hook


def test_delete_hook_has_on_success_invalidate() -> None:
    route = _route("DELETE", "/api/products/{id}", "delete_product")
    hooks = _route_to_hooks(route, {"Product"})
    hook = hooks[0]
    assert "onSuccess" in hook
    assert "invalidateQueries" in hook
    assert "'products'" in hook


def test_delete_hook_no_data_param() -> None:
    route = _route("DELETE", "/api/products/{id}", "delete_product")
    hooks = _route_to_hooks(route, {"Product"})
    hook = hooks[0]
    # DELETE hook should not have a 'data:' param
    assert "data: " not in hook


def test_patch_hook_generates_mutation() -> None:
    route = _route("PATCH", "/api/products/{id}", "patch_product")
    hooks = _route_to_hooks(route, {"Product"})
    hook = hooks[0]
    assert "useMutation" in hook
    assert "apiClient.patch" in hook


# ---------------------------------------------------------------------------
# ApiError interface
# ---------------------------------------------------------------------------


def test_api_error_interface_contains_fields() -> None:
    assert "ApiError" in API_ERROR_INTERFACE
    assert "message: string" in API_ERROR_INTERFACE
    assert "status: number" in API_ERROR_INTERFACE
    assert "detail?" in API_ERROR_INTERFACE


# ---------------------------------------------------------------------------
# sync api-client CLI command
# ---------------------------------------------------------------------------


def test_sync_api_client_base_url_flag(tmp_path: Path) -> None:
    """--base-url appears in generated file."""
    from typer.testing import CliRunner

    from mattstack.commands.sync import sync_app

    backend = tmp_path / "backend"
    backend.mkdir()
    routes_file = backend / "api.py"
    routes_file.write_text(
        "from django_ninja import Router\nrouter = Router()\n\n"
        "@router.get('/api/products/')\ndef list_products(request): ...\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        sync_app,
        [
            "api-client",
            "--path",
            str(tmp_path),
            "--base-url",
            "https://api.example.com",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "https://api.example.com" in result.output


def test_sync_api_client_includes_api_error(tmp_path: Path) -> None:
    """Generated output includes ApiError interface."""
    from typer.testing import CliRunner

    from mattstack.commands.sync import sync_app

    backend = tmp_path / "backend"
    backend.mkdir()
    routes_file = backend / "api.py"
    routes_file.write_text(
        "from django_ninja import Router\nrouter = Router()\n\n"
        "@router.post('/api/products/')\ndef create_product(request): return {}\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        sync_app,
        ["api-client", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "ApiError" in result.output


def test_sync_api_client_mutation_imports_query_client(tmp_path: Path) -> None:
    """useMutation routes add useQueryClient to imports."""
    from typer.testing import CliRunner

    from mattstack.commands.sync import sync_app

    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "api.py").write_text(
        "from django_ninja import Router\nrouter = Router()\n\n"
        "@router.post('/api/items/')\ndef create_item(request): return {}\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        sync_app,
        ["api-client", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "useQueryClient" in result.output


def test_sync_api_client_paginated_imports_keep_previous(tmp_path: Path) -> None:
    """List routes with known types add keepPreviousData to imports."""
    from typer.testing import CliRunner

    from mattstack.commands.sync import sync_app

    backend = tmp_path / "backend"
    backend.mkdir()
    schemas_file = backend / "schemas.py"
    schemas_file.write_text(
        "from pydantic import BaseModel\n\nclass Item(BaseModel):\n    name: str\n"
    )
    (backend / "api.py").write_text(
        "from django_ninja import Router\nrouter = Router()\n\n"
        "@router.get('/api/items/')\ndef list_items(request): return []\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        sync_app,
        ["api-client", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "keepPreviousData" in result.output
