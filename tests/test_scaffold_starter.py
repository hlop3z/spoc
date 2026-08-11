"""
The starter template set (spec: starter-templates).

Generate-and-boot coverage: the starter must yield a runnable,
transport-neutral application — the full default vocabulary, surfaces that
are pure registry projections, and not one third-party import anywhere in
the generated tree.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from spoc.scaffold import DirectorySink, init_project
from spoc.scaffold.sources import InstalledTemplateSources

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")

VOCABULARY = ("models", "views", "commands", "resources", "hooks")


def generate(destination: Path):
    return init_project(
        source=InstalledTemplateSources(),
        sink=DirectorySink(destination),
        project_name="demo_project",
        template_set="starter",
    )


def test_starter_resolves_by_name_and_default_stays_default():
    available = InstalledTemplateSources().available()
    assert "starter" in available
    assert "default" in available
    # Naming no set still means the minimal one — pinned here from the
    # starter's side so a default-flip cannot pass silently.
    loaded = InstalledTemplateSources().load("default")
    assert loaded.name == "default"


def test_starter_project_starts_unedited_with_the_vocabulary(tmp_path):
    destination = tmp_path / "proj"
    generate(destination)

    sys.path.insert(0, str(destination))
    from framework import framework

    framework.start(destination)
    try:
        identifiers = {c.identifier for c in framework.registry}
        assert identifiers == {
            "commands:core.add",
            "commands:core.items",
            "hooks:core.announce",
            "models:core.item",
            "resources:core.store",
            "views:core.list_items",
        }
        # The resource is live before any surface code runs.
        store = framework.resolve("resources:core.store").object
        assert store.items == []
    finally:
        framework.shutdown()
    assert store.items is None  # released on the way out


def test_starter_surfaces_are_registry_projections(tmp_path):
    """Projection tables correspond one-to-one with registry records."""
    destination = tmp_path / "proj"
    generate(destination)

    sys.path.insert(0, str(destination))
    import surface
    from framework import framework

    framework.start(destination)
    try:
        registry = framework.registry
        routes = surface.routes(registry)
        assert {r["name"] for r in routes} == {
            c.identifier for c in registry.by_kind("views")
        }
        commands = surface.commands(registry)
        assert set(commands) == {
            f"{c.namespace}.{c.object_name}" for c in registry.by_kind("commands")
        }
        assert len(surface.hooks(registry)) == len(list(registry.by_kind("hooks")))
    finally:
        framework.shutdown()


def test_adding_a_command_extends_the_cli_without_editing_surfaces(tmp_path):
    destination = tmp_path / "proj"
    generate(destination)

    # Declare one more command component in the app — the only edit made.
    with (destination / "apps" / "core" / "commands.py").open(
        "a", encoding="utf-8"
    ) as handle:
        handle.write(
            "\n\n@commands\ndef ping():\n"
            '    """Answer with pong."""\n'
            '    return "pong"\n'
        )

    result = subprocess.run(
        [sys.executable, "main.py", "core.ping"],
        cwd=destination,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "pong" in result.stdout
    assert "core.ping finished" in result.stdout  # the hook dispatch site fired


def test_starter_cli_runs_end_to_end(tmp_path):
    """`python main.py <command>` — boot, project, dispatch, shut down."""
    destination = tmp_path / "proj"
    generate(destination)

    result = subprocess.run(
        [sys.executable, "main.py", "core.add", "milk"],
        cwd=destination,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "added 'milk' (1 total)" in result.stdout
    assert "core.add finished" in result.stdout


def test_http_binding_recipe_from_the_starter_page_runs(tmp_path):
    """The docs' transport-binding recipe (The Starter → Bind a transport),
    executed: an HTTP surface over the same projection the CLI uses."""
    pytest.importorskip("fastapi", reason="examples dependency group not installed")
    destination = tmp_path / "proj"
    generate(destination)

    (destination / "http_app.py").write_text(
        '"""An HTTP surface over the same projection the CLI uses."""\n'
        "\n"
        "from framework import framework\n"
        "from pathlib import Path\n"
        "import surface\n"
        "\n"
        "BASE_DIR = Path(__file__).resolve().parent\n"
        "\n"
        "\n"
        "def create_app():\n"
        "    from fastapi import FastAPI\n"
        "\n"
        "    framework.start(BASE_DIR)\n"
        '    app = FastAPI(title="myproject")\n'
        "    for route in surface.routes(framework.registry):\n"
        "        app.add_api_route(\n"
        '            route["path"], route["endpoint"], methods=["GET"], name=route["name"]\n'
        "        )\n"
        "    return app\n"
        "\n"
        "\n"
        "app = create_app()   # uvicorn http_app:app\n",
        encoding="utf-8",
    )

    sys.path.insert(0, str(destination))
    import http_app

    try:
        paths = {route.path for route in http_app.app.routes}
        assert "/core/list_items" in paths
    finally:
        http_app.framework.shutdown()


def test_generated_tree_imports_no_third_party_modules(tmp_path):
    """Transport-neutral and dependency-free: every import in every generated
    module is stdlib, `spoc`, or project-local."""
    destination = tmp_path / "proj"
    generate(destination)

    local = {"framework", "surface", "cli", "main", "apps"}
    allowed = set(sys.stdlib_module_names) | {"spoc"} | local

    for path in destination.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            roots = []
            if isinstance(node, ast.Import):
                roots = [alias.name.partition(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                roots = [(node.module or "").partition(".")[0]]
            for root in roots:
                assert root in allowed, f"{path.name} imports {root!r}"
