"""
Framework tests: single declaration point, kind() handles, inert
construction, explicit start/shutdown, on_ready, and instance-scoped
composition (no globals).
"""

import sys
import textwrap
from pathlib import Path

import pytest

import spoc
from spoc import Framework
from spoc.core.exceptions import (
    AppNotFoundError,
    ComponentKindMismatchError,
    InvalidSegmentError,
    SpocError,
    UnknownKindError,
    UnknownNamespaceError,
)

MODELS_BODY = """
    from spoc import component

    @component(metadata={"type": "models"})
    class post:
        ...
"""


def make_project(
    tmp_path: Path, app: str, models_body: str = MODELS_BODY, extra_toml: str = ""
) -> Path:
    """Build a minimal SPOC project with one app on disk. No settings.py."""
    base = tmp_path / f"proj_{app}"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(
        textwrap.dedent(
            f"""
            [spoc]
            mode = "development"
            debug = true

            [spoc.apps]
            development = ["{app}"]
            """
        )
        + extra_toml
    )
    app_dir = base / "apps" / app
    app_dir.mkdir(parents=True)
    (app_dir / "__init__.py").write_text("")
    (app_dir / "models.py").write_text(textwrap.dedent(models_body))
    return base


@pytest.fixture(autouse=True)
def clean_sys_path_and_modules():
    """Keep app imports from leaking between tests."""
    path_before = list(sys.path)
    modules_before = set(sys.modules)
    yield
    sys.path[:] = path_before
    for name in set(sys.modules) - modules_before:
        del sys.modules[name]


# ── Declaration ───────────────────────────────────────────────────────────


def test_kind_handle_bare_and_named_forms():
    fw = Framework("models")
    model = fw.kind("models")

    @model
    class post: ...

    @model(name="user_account")
    class UserAccount: ...

    post_info = spoc.get_info(post)
    account_info = spoc.get_info(UserAccount)
    assert post_info is not None and account_info is not None
    assert post_info.name == "post"
    assert post_info.metadata["type"] == "models"
    assert account_info.name == "user_account"


def test_kind_handle_rejects_nonconforming_name_without_explicit():
    fw = Framework("models")
    model = fw.kind("models")
    with pytest.raises(InvalidSegmentError):

        @model
        class PascalCase: ...


def test_kind_handle_for_undeclared_kind():
    fw = Framework("models", "views")
    with pytest.raises(UnknownKindError) as exc:
        fw.kind("controllers")
    message = str(exc.value)
    assert "controllers" in message
    assert "models" in message and "views" in message


def test_dependencies_must_reference_declared_kinds():
    with pytest.raises(UnknownKindError):
        Framework("models", dependencies={"views": ["models"]})
    with pytest.raises(UnknownKindError):
        Framework("models", "views", dependencies={"views": ["schemas"]})


def test_construction_is_inert(tmp_path):
    """No sys.path mutation, no filesystem writes, in an empty directory."""
    path_before = list(sys.path)
    fw = Framework("models", "views", dependencies={"views": ["models"]})
    assert sys.path == path_before
    assert list(tmp_path.iterdir()) == []
    assert fw.started is False


# ── Lifecycle ─────────────────────────────────────────────────────────────


def test_start_discovers_and_resolve_works(tmp_path):
    base = make_project(
        tmp_path,
        "blog",
        """
        from spoc import component

        @component(metadata={"type": "models"})
        class post:
            ...

        @component(name="comment_thread", metadata={"type": "models"})
        class CommentThread:
            ...
        """,
    )
    fw = Framework("models").start(base)

    assert fw.started is True
    identifiers = [c.identifier for c in fw.registry]
    assert identifiers == ["models:blog.comment_thread", "models:blog.post"]

    record = fw.resolve("models:blog.post")
    assert record.kind == "models"
    assert record.namespace == "blog"
    assert record.name == "post"


def test_double_start_raises(tmp_path):
    base = make_project(tmp_path, "once")
    fw = Framework("models").start(base)
    with pytest.raises(SpocError, match="already started"):
        fw.start(base)


def test_shutdown_without_start_is_noop():
    fw = Framework("models")
    assert fw.shutdown() is fw
    assert fw.started is False


def test_kind_location_mismatch_fails_start(tmp_path):
    """A views component declared in models.py is a start error, not a drop."""
    base = make_project(
        tmp_path,
        "mismatch",
        """
        from spoc import component

        @component(metadata={"type": "views"})
        def list_posts():
            ...
        """,
    )
    fw = Framework("models")
    with pytest.raises(ComponentKindMismatchError) as exc:
        fw.start(base)
    message = str(exc.value)
    assert "list_posts" in message
    assert "views" in message and "models" in message
    assert fw.started is False


def test_settings_module_is_never_read(tmp_path):
    """Only spoc.toml is consulted: a poison settings.py changes nothing."""
    base = make_project(tmp_path, "toml_only")
    (base / "config" / "__init__.py").write_text("")
    (base / "config" / "settings.py").write_text(
        "raise RuntimeError('spoc must never import settings.py')\n"
    )
    fw = Framework("models").start(base)
    assert [c.identifier for c in fw.registry] == ["models:toml_only.post"]


def test_handles_taken_before_start(tmp_path):
    """Apps import the framework's own handles; marks land after discovery."""
    base = make_project(
        tmp_path,
        "handleapp",
        """
        from fwdef import model

        @model
        class post:
            ...
        """,
    )
    (base / "apps" / "fwdef.py").write_text(
        "import spoc\n"
        'framework = spoc.Framework("models")\n'
        'model = framework.kind("models")\n'
    )
    sys.path.insert(0, str(base / "apps"))
    import fwdef

    fwdef.framework.start(base)
    assert [c.identifier for c in fwdef.framework.registry] == ["models:handleapp.post"]


# ── on_ready ──────────────────────────────────────────────────────────────


def test_on_ready_fires_once_with_full_registry_in_order(tmp_path):
    base = make_project(tmp_path, "readyapp")
    fw = Framework("models")
    calls: list[tuple[str, list[str]]] = []

    @fw.on_ready
    def first(registry):
        calls.append(("first", [c.identifier for c in registry]))

    @fw.on_ready
    def second(registry):
        calls.append(("second", [c.identifier for c in registry]))

    fw.start(base)
    assert calls == [
        ("first", ["models:readyapp.post"]),
        ("second", ["models:readyapp.post"]),
    ]


def test_on_ready_failure_fails_start(tmp_path):
    base = make_project(tmp_path, "readyfail")
    fw = Framework("models")

    @fw.on_ready
    def boom(registry):
        raise ValueError("finalize failed")

    with pytest.raises(ValueError, match="finalize failed"):
        fw.start(base)
    assert fw.started is False


def test_on_ready_runs_before_module_initialization(tmp_path):
    base = make_project(
        tmp_path,
        "orderapp",
        MODELS_BODY
        + """
    def initialize():
        import fwprobe
        fwprobe.events.append("initialize")
    """,
    )
    (base / "apps" / "fwprobe.py").write_text("events = []\n")
    sys.path.insert(0, str(base / "apps"))
    import fwprobe

    fw = Framework("models")

    @fw.on_ready
    def ready(registry):
        fwprobe.events.append("ready")

    fw.start(base)
    assert fwprobe.events == ["ready", "initialize"]


# ── Per-kind lifecycle hooks ──────────────────────────────────────────────


def test_on_startup_and_on_shutdown_hooks_receive_components(tmp_path):
    base = make_project(tmp_path, "hookapp")
    fw = Framework("models")
    seen: list[tuple[str, set]] = []

    @fw.on_startup("models")
    def up(objects):
        seen.append(("up", {type(o).__name__ or o.__name__ for o in objects}))

    @fw.on_shutdown("models")
    def down(objects):
        seen.append(("down", set()))

    fw.start(base)
    fw.shutdown()
    assert [tag for tag, _ in seen] == ["up", "down"]
    assert fw.started is False


def test_hooks_for_undeclared_kind_fail():
    fw = Framework("models")
    with pytest.raises(UnknownKindError):
        fw.on_startup("views")
    with pytest.raises(UnknownKindError):
        fw.on_shutdown("views")


# ── Configuration behavior through start ──────────────────────────────────


def test_mode_cascade():
    apps = {
        "production": ["auth"],
        "staging": ["admin"],
        "development": ["demo"],
    }
    assert Framework._collect_apps("development", apps) == ["demo", "admin", "auth"]
    assert Framework._collect_apps("staging", apps) == ["admin", "auth"]
    assert Framework._collect_apps("production", apps) == ["auth"]


def test_unresolvable_plugin_fails_start(tmp_path):
    base = make_project(
        tmp_path,
        "plugapp",
        extra_toml='\n[spoc.plugins]\nhooks = ["no_such_module.attr"]\n',
    )
    fw = Framework("models")
    with pytest.raises(AppNotFoundError, match="no_such_module"):
        fw.start(base)
    assert fw.started is False


def test_declared_plugin_loads(tmp_path):
    base = make_project(
        tmp_path,
        "plugok",
        extra_toml='\n[spoc.plugins]\nhooks = ["plugok.extras.hook"]\n',
    )
    (base / "apps" / "plugok" / "extras.py").write_text(
        "def hook():\n    return 'loaded'\n"
    )
    fw = Framework("models").start(base)
    assert fw.plugins["hooks"]["plugok.extras.hook"]() == "loaded"


# ── Independence and removed API ──────────────────────────────────────────


def test_two_frameworks_are_independent(tmp_path):
    """De-globalized composition: registries, handles, hooks never leak."""
    base_a = make_project(
        tmp_path,
        "alpha",
        """
        from spoc import component

        @component(metadata={"type": "models"})
        class post:
            ...
        """,
    )
    base_b = make_project(
        tmp_path,
        "beta",
        """
        from spoc import component

        @component(metadata={"type": "models"})
        class order:
            ...
        """,
    )
    hooks_seen: list[str] = []
    fw_a = Framework("models")
    fw_b = Framework("models")
    fw_b.on_startup("models")(lambda objects: hooks_seen.append("b"))

    fw_a.start(base_a)
    fw_b.start(base_b)

    assert [c.identifier for c in fw_a.registry] == ["models:alpha.post"]
    assert [c.identifier for c in fw_b.registry] == ["models:beta.order"]
    assert fw_a.importer is not fw_b.importer
    assert fw_a.registry is not fw_b.registry
    # fw_b's hook ran for fw_b only; fw_a's importer never saw it
    assert hooks_seen == ["b"]
    assert not fw_a.importer.module_hooks.pattern
    with pytest.raises(UnknownNamespaceError):
        fw_a.resolve("models:beta.order")


def test_removed_api_is_absent():
    """Green-field: the old declaration surface is gone, not deprecated."""
    for gone in (
        "Components",
        "Schema",
        "Hook",
        "load_configuration",
        "DependencyGraph",
    ):
        assert not hasattr(spoc, gone), gone
    fw = Framework("models")
    assert not hasattr(fw, "get_component")
    assert not hasattr(type(fw), "components")
