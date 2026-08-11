"""
The reference application (spec: reference-application).

These tests boot the real `examples/` tree — the example is the fixture —
so a kernel change that breaks the worked storefront fails this suite like
any other regression. FastAPI-dependent tests skip locally when the
`examples` dependency group is absent; CI installs it, so the projection is
genuinely constructed there.
"""

import asyncio
import importlib
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parent.parent / "examples"

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")


def _example_framework():
    """The example's own declaration, imported from its tree."""
    sys.path.insert(0, str(EXAMPLES))
    return importlib.import_module("framework").framework


def test_storefront_boots_and_registers_the_domain():
    fw = _example_framework().start(EXAMPLES)
    try:
        identifiers = [c.identifier for c in fw.registry]
        assert identifiers == [
            "hooks:extras.hook",
            "middleware:extras.middleware",
            "models:auth.role",
            "models:auth.user_account",
            "models:catalog.product",
            "models:orders.order",
            "resources:catalog.search_index",
            "views:catalog.find_product",
            "views:catalog.list_products",
            "views:orders.order_summary",
        ]
    finally:
        fw.shutdown()


def test_cross_namespace_resolution_at_runtime():
    """orders reaches catalog through the registry while handling a call."""
    fw = _example_framework().start(EXAMPLES)
    try:
        summary = fw.resolve("views:orders.order_summary").object()
        assert summary["total_cents"] == 2 * 7900
        assert summary["product"]["name"] == "keyboard"
    finally:
        fw.shutdown()


def test_resource_opened_at_start_reached_mid_call_and_released():
    """The vocabulary's resource recipe, observed at both ends.

    The kind's startup hook opens the resource before any view runs; a view in
    another module reaches it through the registry while handling a call; the
    shutdown hook has released it by the time shutdown returns.
    """
    fw = _example_framework().start(EXAMPLES)
    index = fw.resolve("resources:catalog.search_index").object
    try:
        assert index.events == ["open"]  # opened by the kind's hook, exactly once
        hit = fw.resolve("views:catalog.find_product").object("mouse")
        assert hit["product"]["name"] == "mouse"  # reached live, mid-call
    finally:
        fw.shutdown()
    assert index.events == ["open", "close"]  # released on the way out
    assert index.entries is None


def test_module_lifecycle_seeds_and_clears_the_stock():
    fw = _example_framework().start(EXAMPLES)
    catalog_models = importlib.import_module("apps.catalog.models")
    assert len(catalog_models.PRODUCTS) == 2
    fw.shutdown()
    assert catalog_models.PRODUCTS == {}


def test_async_entry_awaits_hooks_on_the_async_path():
    sys.path.insert(0, str(EXAMPLES))
    async_main = importlib.import_module("async_main")
    fw = async_main.framework

    async def run():
        await fw.astart(EXAMPLES)
        assert fw.resolve("models:catalog.product").object.__name__ == "Product"
        # The resource recipe's async twin: coroutine hooks opened it, awaited.
        index = fw.resolve("resources:catalog.search_index").object
        assert index.entries is not None
        await fw.ashutdown()
        assert index.entries is None

    asyncio.run(run())
    assert fw.started is False


def test_http_projection_derives_from_the_registry():
    """Every projected route corresponds to a registry record."""
    fw = _example_framework().start(EXAMPLES)
    try:
        http_app = importlib.import_module("http_app")
        routes = http_app.build_routes(fw.registry)
        assert {r["path"] for r in routes} == {
            "/catalog/find_product",
            "/catalog/list_products",
            "/orders/order_summary",
        }
        assert all(r["name"] in fw.registry for r in routes)
    finally:
        fw.shutdown()


def test_fastapi_app_constructs_from_the_projection():
    pytest.importorskip("fastapi", reason="examples dependency group not installed")
    sys.path.insert(0, str(EXAMPLES))
    http_app = importlib.import_module("http_app")
    app = http_app.create_app()
    paths = {route.path for route in app.routes}
    assert {"/catalog/list_products", "/orders/order_summary"} <= paths


def test_reference_project_passes_spoc_check():
    """The diagnostics and the reference app agree with each other."""
    from spoc.diagnostics import check

    # No explicit ref: the reference app now sits on the same convention
    # `spoc init` emits, so the diagnostics locate it like any generated project.
    report = check(EXAMPLES)
    assert report.ok, [f.message for f in report.findings]


def test_sync_entry_runs_to_completion():
    """`python main.py` — the front-door experience — exits cleanly."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=EXAMPLES,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Order total: 15800 cents" in result.stdout
    assert "Search hit: mouse" in result.stdout
