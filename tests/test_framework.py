"""
Framework integration tests: discovery into the registry, loud failures,
resolve(), and instance-scoped composition (no globals).
"""

import sys
import textwrap
from pathlib import Path

import pytest

from spoc import Framework, Schema
from spoc.core.exceptions import ComponentKindMismatchError, UnknownNamespaceError


def make_project(tmp_path: Path, app: str, models_body: str) -> Path:
    """Build a minimal SPOC project with one app on disk."""
    base = tmp_path / f"proj_{app}"
    (base / "config").mkdir(parents=True)
    (base / "config" / "__init__.py").write_text("")
    (base / "config" / "settings.py").write_text(
        textwrap.dedent(
            f"""
            from pathlib import Path
            BASE_DIR = Path(__file__).resolve().parent.parent
            INSTALLED_APPS = ["{app}"]
            PLUGINS = {{}}
            """
        )
    )
    (base / "config" / "spoc.toml").write_text(
        '[spoc]\nmode = "development"\ndebug = true\n\n[spoc.apps]\n\n[spoc.plugins]\n'
    )
    app_dir = base / "apps" / app
    app_dir.mkdir(parents=True)
    (app_dir / "__init__.py").write_text("")
    (app_dir / "models.py").write_text(textwrap.dedent(models_body))
    return base


DECLARATION_HEADER = """
        from spoc import Components
        components = Components("models")
"""


@pytest.fixture(autouse=True)
def clean_sys_path_and_modules():
    """Keep app imports from leaking between tests."""
    path_before = list(sys.path)
    modules_before = set(sys.modules)
    yield
    sys.path[:] = path_before
    for name in set(sys.modules) - modules_before:
        del sys.modules[name]


def test_discovery_populates_registry_and_resolve_works(tmp_path):
    base = make_project(
        tmp_path,
        "blog",
        DECLARATION_HEADER
        + """
        @components.register("models")
        class post:
            ...

        @components.register("models", name="comment_thread")
        class CommentThread:
            ...
        """,
    )
    framework = Framework(base_dir=base, schema=Schema(modules=["models"]))

    identifiers = [c.identifier for c in framework.registry]
    assert identifiers == ["models:blog.comment_thread", "models:blog.post"]

    record = framework.resolve("models:blog.post")
    assert record.kind == "models"
    assert record.namespace == "blog"
    assert record.name == "post"


def test_kind_location_mismatch_fails_startup(tmp_path):
    """A views component declared in models.py is a startup error, not a drop."""
    base = make_project(
        tmp_path,
        "mismatch",
        """
        from spoc import Components
        components = Components("models", "views")

        @components.register("views")
        def list_posts():
            ...
        """,
    )
    with pytest.raises(ComponentKindMismatchError) as exc:
        Framework(base_dir=base, schema=Schema(modules=["models"]))
    message = str(exc.value)
    assert "list_posts" in message
    assert "views" in message and "models" in message


def test_imported_objects_register_where_defined_only(tmp_path):
    base = make_project(
        tmp_path,
        "importer_app",
        DECLARATION_HEADER
        + """
        @components.register("models")
        class post:
            ...
        """,
    )
    # A second module of the same kind importing the first's component
    (base / "apps" / "importer_app" / "views.py").write_text(
        "from importer_app.models import post\n"
    )
    framework = Framework(base_dir=base, schema=Schema(modules=["models", "views"]))
    assert [c.identifier for c in framework.registry] == ["models:importer_app.post"]


def test_two_frameworks_are_independent(tmp_path):
    """De-globalized composition: registries and hooks never leak (D7)."""
    base_a = make_project(
        tmp_path,
        "alpha",
        DECLARATION_HEADER
        + """
        @components.register("models")
        class post:
            ...
        """,
    )
    base_b = make_project(
        tmp_path,
        "beta",
        DECLARATION_HEADER
        + """
        @components.register("models")
        class order:
            ...
        """,
    )
    hooks_seen: list[str] = []
    fw_a = Framework(base_dir=base_a, schema=Schema(modules=["models"]))
    fw_b = Framework(
        base_dir=base_b,
        schema=Schema(
            modules=["models"],
            hooks={"models": {"startup": lambda m: hooks_seen.append("b")}},
        ),
    )

    assert [c.identifier for c in fw_a.registry] == ["models:alpha.post"]
    assert [c.identifier for c in fw_b.registry] == ["models:beta.order"]
    assert fw_a.importer is not fw_b.importer
    assert fw_a.registry is not fw_b.registry
    # fw_b's hook ran for fw_b only; fw_a's importer never saw it
    assert hooks_seen == ["b"]
    assert not fw_a.importer.module_hooks.pattern
    with pytest.raises(UnknownNamespaceError):
        fw_a.resolve("models:beta.order")


def test_no_legacy_lookup_surface(tmp_path):
    """get_component and the namespace-of-dicts view are gone."""
    base = make_project(tmp_path, "clean", DECLARATION_HEADER)
    framework = Framework(base_dir=base, schema=Schema(modules=["models"]))
    assert not hasattr(framework, "get_component")
    assert not hasattr(type(framework), "components")
