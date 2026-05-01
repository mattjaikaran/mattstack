"""Tests for generate command — Phase 16A-16D: model, schema, controller, admin; Phase 17: crud."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from mattstack.commands.generate import (
    _build_admin_file,
    _generate_api_controller,
    _generate_django_model,
    _generate_pydantic_schema,
    _generate_pytest_api_tests,
    _generate_react_list_component,
    _generate_tanstack_hooks,
    _generate_ts_api_client,
    _generate_vitest_component_test,
    _parse_fields,
    _to_pascal,
    _to_snake,
    _update_init_import,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_backend(tmp_path: Path, app: str = "core") -> Path:
    """Minimal backend structure under tmp_path."""
    backend = tmp_path / "backend"
    apps_dir = backend / "apps" / app
    apps_dir.mkdir(parents=True)
    (apps_dir / "__init__.py").write_text("")
    return tmp_path


# ---------------------------------------------------------------------------
# 1. AbstractBaseModel — model file imports AbstractBaseModel
# ---------------------------------------------------------------------------


def test_model_uses_abstract_base_model() -> None:
    fields = _parse_fields(["title:str", "price:decimal"])
    source = _generate_django_model("Product", fields)
    assert "AbstractBaseModel" in source
    assert "from core.models.base import AbstractBaseModel" in source
    assert "class Product(AbstractBaseModel):" in source


# ---------------------------------------------------------------------------
# 2. @http_* decorators — controller uses ninja-extra decorators
# ---------------------------------------------------------------------------


def test_controller_uses_http_decorators() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_api_controller("Product", fields, "core")
    assert "@http_get" in source
    assert "@http_post" in source
    assert "@http_put" in source
    assert "@http_delete" in source
    assert "from ninja_extra import api_controller" in source


# ---------------------------------------------------------------------------
# 3. model_dump() — controller uses model_dump(), not .dict()
# ---------------------------------------------------------------------------


def test_controller_uses_model_dump_not_dict() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_api_controller("Product", fields, "core")
    assert "model_dump()" in source
    assert ".dict(" not in source


# ---------------------------------------------------------------------------
# 4. --empty guard — model with no fields and no --empty exits code 1
# ---------------------------------------------------------------------------


def test_model_command_no_fields_no_empty_exits(tmp_path: Path) -> None:
    _make_backend(tmp_path)

    from mattstack.commands.generate import model as model_cmd
    from typer.testing import CliRunner
    import typer

    app = typer.Typer()
    app.command()(model_cmd)
    runner = CliRunner()

    result = runner.invoke(app, ["Product", "--path", str(tmp_path)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# 5. FK validation — FK target file missing exits with error
# ---------------------------------------------------------------------------


def test_fk_missing_target_exits(tmp_path: Path) -> None:
    _make_backend(tmp_path)

    from mattstack.commands.generate import model as model_cmd
    from typer.testing import CliRunner
    import typer

    app = typer.Typer()
    app.command()(model_cmd)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["OrderItem", "--fields", "order:fk:Order", "--path", str(tmp_path)],
    )
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# 6. models/__init__.py wiring — import line appended
# ---------------------------------------------------------------------------


def test_update_init_import_appends_line(tmp_path: Path) -> None:
    init_file = tmp_path / "__init__.py"
    init_file.write_text("")

    added = _update_init_import(init_file, "from .product import Product", dry_run=False)

    assert added is True
    content = init_file.read_text()
    assert "from .product import Product" in content


def test_update_init_import_no_duplicate(tmp_path: Path) -> None:
    init_file = tmp_path / "__init__.py"
    init_file.write_text("from .product import Product\n")

    added = _update_init_import(init_file, "from .product import Product", dry_run=False)

    assert added is False
    assert init_file.read_text().count("from .product import Product") == 1


# ---------------------------------------------------------------------------
# 7. Admin file creation — content is valid unfold admin
# ---------------------------------------------------------------------------


def test_admin_file_has_unfold_import() -> None:
    fields = _parse_fields(["title:str", "price:decimal"])
    source = _build_admin_file("Product", "product", "core", fields)
    assert "from unfold.admin import ModelAdmin" in source
    assert "@admin.register(Product)" in source
    assert "class ProductAdmin(ModelAdmin):" in source


def test_admin_file_list_display_includes_str_fields() -> None:
    fields = _parse_fields(["title:str", "slug:str"])
    source = _build_admin_file("Product", "product", "core", fields)
    assert '"title"' in source
    assert '"slug"' in source
    assert '"created_at"' in source


# ---------------------------------------------------------------------------
# 8. admin/__init__.py wiring — admin import wired via _update_init_import
# ---------------------------------------------------------------------------


def test_admin_init_wiring(tmp_path: Path) -> None:
    admin_init = tmp_path / "admin" / "__init__.py"
    admin_init.parent.mkdir(parents=True)
    admin_init.write_text("")

    added = _update_init_import(admin_init, "from .product_admin import ProductAdmin", dry_run=False)

    assert added is True
    assert "from .product_admin import ProductAdmin" in admin_init.read_text()


# ---------------------------------------------------------------------------
# 9. 4-schema pattern — Base/Create/Update/Response classes all present
# ---------------------------------------------------------------------------


def test_schema_four_class_pattern() -> None:
    fields = _parse_fields(["title:str", "price:decimal"])
    source = _generate_pydantic_schema("Product", fields)
    assert "class ProductBaseSchema(Schema):" in source
    assert "class ProductCreateSchema(ProductBaseSchema):" in source
    assert "class ProductUpdateSchema(ProductBaseSchema):" in source
    assert "class ProductResponseSchema(ProductBaseSchema):" in source


def test_schema_response_has_from_attributes() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_pydantic_schema("Product", fields)
    assert "model_config = ConfigDict(from_attributes=True)" in source
    assert "id: UUID" in source
    assert "created_at: datetime" in source
    assert "updated_at: datetime" in source


# ---------------------------------------------------------------------------
# Phase 17: generate crud — TS API client
# ---------------------------------------------------------------------------


def test_ts_api_client_exports_all_crud_functions() -> None:
    fields = _parse_fields(["title:str", "price:decimal"])
    source = _generate_ts_api_client("Product", fields)
    assert "export async function listProducts" in source
    assert "export async function getProduct" in source
    assert "export async function createProduct" in source
    assert "export async function updateProduct" in source
    assert "export async function deleteProduct" in source


def test_ts_api_client_contains_type_interfaces() -> None:
    fields = _parse_fields(["title:str", "price:decimal"])
    source = _generate_ts_api_client("Product", fields)
    assert "export interface Product {" in source
    assert "export interface ProductCreate {" in source
    assert "export interface ProductUpdate {" in source


def test_ts_api_client_field_types_mapped() -> None:
    fields = _parse_fields(["title:str", "active:bool", "price:decimal"])
    source = _generate_ts_api_client("Product", fields)
    assert "title: string;" in source
    assert "active: boolean;" in source
    assert "price: number;" in source


# ---------------------------------------------------------------------------
# Phase 17: generate crud — TanStack hooks
# ---------------------------------------------------------------------------


def test_tanstack_hooks_exports_all_five_hooks() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_tanstack_hooks("Product", fields)
    assert "export function useProductList" in source
    assert "export function useProduct(" in source
    assert "export function useCreateProduct" in source
    assert "export function useUpdateProduct" in source
    assert "export function useDeleteProduct" in source


def test_tanstack_hooks_uses_invalidate_queries() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_tanstack_hooks("Product", fields)
    assert 'invalidateQueries({ queryKey: ["products"]' in source


def test_tanstack_hooks_imports_tanstack_query() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_tanstack_hooks("Product", fields)
    assert 'from "@tanstack/react-query"' in source
    assert "useQuery" in source
    assert "useMutation" in source
    assert "useQueryClient" in source


# ---------------------------------------------------------------------------
# Phase 17: generate crud — React list component
# ---------------------------------------------------------------------------


def test_react_list_component_has_loading_state() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_react_list_component("Product", fields)
    assert "Loading products..." in source


def test_react_list_component_has_error_state() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_react_list_component("Product", fields)
    assert "error" in source.lower()
    assert "(error as Error).message" in source


def test_react_list_component_has_empty_state() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_react_list_component("Product", fields)
    assert "No products found." in source


def test_react_list_component_uses_hook() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_react_list_component("Product", fields)
    assert "useProductList" in source
    assert 'from "@/hooks/useProducts"' in source


# ---------------------------------------------------------------------------
# Phase 17: generate crud — pytest API tests
# ---------------------------------------------------------------------------


def test_pytest_api_tests_covers_all_five_endpoints() -> None:
    fields = _parse_fields(["title:str", "price:decimal"])
    source = _generate_pytest_api_tests("Product", fields, "core")
    assert "test_list_products_returns_200" in source
    assert "test_get_product_not_found" in source
    assert "test_create_product_unauthenticated" in source
    assert "test_update_product_unauthenticated" in source
    assert "test_delete_product_unauthenticated" in source


def test_pytest_api_tests_imports_model() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_pytest_api_tests("Product", fields, "core")
    assert "from apps.core.models.product import Product" in source


def test_pytest_api_tests_checks_auth_status_codes() -> None:
    fields = _parse_fields(["title:str"])
    source = _generate_pytest_api_tests("Product", fields, "core")
    assert "401, 403" in source


# ---------------------------------------------------------------------------
# Phase 17: generate crud — Vitest component test
# ---------------------------------------------------------------------------


def test_vitest_component_test_mocks_hook() -> None:
    source = _generate_vitest_component_test("Product")
    assert 'vi.mock("@/hooks/useProducts"' in source
    assert "useProductList" in source


def test_vitest_component_test_checks_empty_state() -> None:
    source = _generate_vitest_component_test("Product")
    assert "No products found." in source


# ---------------------------------------------------------------------------
# Phase 17: generate crud — CLI integration (dry-run)
# ---------------------------------------------------------------------------


def test_crud_command_requires_fields(tmp_path: Path) -> None:
    _make_backend(tmp_path)

    from mattstack.commands.generate import crud as crud_cmd
    from typer.testing import CliRunner

    app = typer.Typer()
    app.command()(crud_cmd)
    runner = CliRunner()

    result = runner.invoke(app, ["Product", "--path", str(tmp_path)])
    assert result.exit_code == 1


def test_crud_command_dry_run_no_files_created(tmp_path: Path) -> None:
    _make_backend(tmp_path)

    from mattstack.commands.generate import crud as crud_cmd
    from typer.testing import CliRunner

    app = typer.Typer()
    app.command()(crud_cmd)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["Product", "--fields", "title:str", "--path", str(tmp_path), "--dry-run"],
    )
    assert result.exit_code == 0
    assert not (tmp_path / "backend" / "apps" / "core" / "models" / "product.py").exists()


def test_crud_command_creates_backend_files(tmp_path: Path) -> None:
    _make_backend(tmp_path)
    (tmp_path / "backend" / "apps" / "core" / "models").mkdir(parents=True, exist_ok=True)

    from mattstack.commands.generate import crud as crud_cmd
    from typer.testing import CliRunner

    app = typer.Typer()
    app.command()(crud_cmd)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["Product", "--fields", "title:str", "--fields", "price:decimal", "--path", str(tmp_path)],
    )
    assert result.exit_code == 0

    backend = tmp_path / "backend" / "apps" / "core"
    assert (backend / "models" / "product.py").exists()
    assert (backend / "schemas" / "product.py").exists()
    assert (backend / "api" / "product.py").exists()
    assert (backend / "admin" / "product_admin.py").exists()


def test_crud_command_with_tests_creates_test_file(tmp_path: Path) -> None:
    _make_backend(tmp_path)

    from mattstack.commands.generate import crud as crud_cmd
    from typer.testing import CliRunner

    app = typer.Typer()
    app.command()(crud_cmd)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["Product", "--fields", "title:str", "--path", str(tmp_path), "--with-tests"],
    )
    assert result.exit_code == 0
    test_file = tmp_path / "backend" / "apps" / "core" / "tests" / "test_product_api.py"
    assert test_file.exists()
    content = test_file.read_text()
    assert "test_list_products_returns_200" in content
