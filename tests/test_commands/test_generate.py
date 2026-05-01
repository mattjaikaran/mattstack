"""Tests for generate command — Phase 16A-16D: model, schema, controller, admin."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from mattstack.commands.generate import (
    _build_admin_file,
    _generate_api_controller,
    _generate_django_model,
    _generate_pydantic_schema,
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
