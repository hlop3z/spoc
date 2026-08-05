"""
Framework tests: single declaration point, kind() handles, inert construction, explicit
start/shutdown, on_ready, per-kind optionality, and instance-scoped composition (no
globals).
"""

import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

import spoc
from spoc import Framework, KindSpec
from spoc.core.config import DEFAULT_MODES
from spoc.core.declaration import get_info
from spoc.core.exceptions import (
    AppNotFoundError,
    ComponentKindMismatchError,
    ConfigurationError,
    InvalidSegmentError,
    MetadataContractError,
    MissingModuleError,
    SpocError,
    UnknownKindError,
    UnknownNamespaceError,
)

MODELS_BODY = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Post:
        ...
"""


def make_project(
    tmp_path: Path,
    app: str,
    models_body: str = MODELS_BODY,
    extra_toml: str = "",
    extra_modules: dict[str, str] | None = None,
) -> Path:
    """Build a minimal SPOC project with one app on disk. No settings.py.

    The app is a top-level package under the project root, declared by its
    dotted path (here a single segment). The test environment — not the
    kernel — makes the root importable, exactly as a real entry point's
    script directory would be.
    """
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
    app_dir = base / app
    app_dir.mkdir(parents=True)
    (app_dir / "__init__.py").write_text("")
    (app_dir / "models.py").write_text(textwrap.dedent(models_body))
    for name, body in (extra_modules or {}).items():
        (app_dir / f"{name}.py").write_text(textwrap.dedent(body))
    sys.path.insert(0, str(base))
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
    class CommentThread: ...  # derived → comment_thread

    @model(name="legacy_user")
    class UserAccount: ...  # explicit → verbatim

    thread_info = get_info(CommentThread)
    account_info = get_info(UserAccount)
    assert thread_info is not None and account_info is not None
    assert thread_info.name == "comment_thread"
    assert thread_info.kind == "models"
    assert account_info.name == "legacy_user"


def test_kind_handle_rejects_stated_nonconforming_name():
    """Explicit names are verbatim: stated, so used or rejected — never converted."""
    fw = Framework("models")
    model = fw.kind("models")
    with pytest.raises(InvalidSegmentError):

        @model(name="PascalCase")
        class Anything: ...


def test_kind_handle_for_undeclared_kind():
    fw = Framework("models", "views")
    with pytest.raises(UnknownKindError) as exc:
        fw.kind("controllers")
    message = str(exc.value)
    assert "controllers" in message
    assert "models" in message and "views" in message


def test_dependencies_must_reference_declared_kinds():
    with pytest.raises(UnknownKindError):
        Framework(KindSpec("views", depends_on=("models",)))
    with pytest.raises(UnknownKindError):
        Framework("models", KindSpec("views", depends_on=("schemas",)))


def test_bare_and_spec_forms_mix_in_one_declaration():
    fw = Framework("models", KindSpec("views", depends_on=("models",), required=False))
    assert fw.kinds == ("models", "views")
    assert fw.spec("models") == KindSpec("models")
    assert fw.spec("views").required is False


def test_construction_is_inert(tmp_path):
    """No sys.path mutation, no filesystem writes, in an empty directory."""
    path_before = list(sys.path)
    fw = Framework("models", KindSpec("views", depends_on=("models",)))
    assert sys.path == path_before
    assert list(tmp_path.iterdir()) == []
    assert fw.started is False


# ── Lifecycle ─────────────────────────────────────────────────────────────


def test_start_discovers_and_resolve_works(tmp_path):
    base = make_project(
        tmp_path,
        "blog",
        """
        from spoc.core.declaration import component

        @component(kind="models")
        class Post:
            ...

        @component(kind="models")
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


def test_lookup_is_never_converted(tmp_path):
    """Derivation converts; resolution does not — one canonical identifier."""
    base = make_project(tmp_path, "exact")
    fw = Framework("models").start(base)

    assert fw.resolve("models:exact.post").name == "post"
    with pytest.raises(InvalidSegmentError):
        fw.resolve("models:exact.Post")


def test_double_start_raises(tmp_path):
    base = make_project(tmp_path, "once")
    fw = Framework("models").start(base)
    with pytest.raises(SpocError, match="already started"):
        fw.start(base)


def test_shutdown_without_start_is_noop():
    fw = Framework("models")
    assert fw.shutdown() is fw
    assert fw.started is False


def test_shutdown_resets_to_a_clean_boot(tmp_path):
    """Restarting on a second project must not resolve the first project's parts."""
    base_a = make_project(tmp_path, "alpha")
    base_b = make_project(tmp_path, "beta")
    fw = Framework("models")

    fw.start(base_a)
    assert fw.resolve("models:alpha.post")
    fw.shutdown()

    fw.start(base_b)
    assert fw.resolve("models:beta.post")
    with pytest.raises(UnknownNamespaceError):
        fw.resolve("models:alpha.post")


def test_restart_rebuilds_registry_without_rerunning_module_code(tmp_path):
    """The honest restart contract: kernel state resets, the module cache
    persists — module-level code runs at most once per process."""
    base = make_project(
        tmp_path,
        "counterapp",
        """
        from pathlib import Path
        from spoc.core.declaration import component

        _marker = Path(__file__).parent / "imports.txt"
        _marker.write_text((_marker.read_text() + "x") if _marker.exists() else "x")

        @component(kind="models")
        class Post:
            ...
        """,
    )
    fw = Framework("models")

    fw.start(base)
    fw.shutdown()
    assert len(fw.registry) == 0

    fw.start(base)
    assert fw.resolve("models:counterapp.post")
    # One "x": the second boot re-ran discovery against the cached module.
    assert (base / "counterapp" / "imports.txt").read_text() == "x"


def test_lifecycle_never_mutates_sys_path(tmp_path):
    """Boot acquires no process-global state: the import path is untouched."""
    base = make_project(tmp_path, "pathless")
    path_before = list(sys.path)

    fw = Framework("models").start(base)
    assert sys.path == path_before
    fw.shutdown()
    assert sys.path == path_before


def test_start_creates_nothing_on_disk(tmp_path):
    """A typo'd or bare project root must not sprout directories."""
    base = tmp_path / "bare"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text('[spoc]\nmode = "development"\n')
    entries_before = set(base.rglob("*"))

    Framework("models").start(base)
    assert set(base.rglob("*")) == entries_before


def test_dotted_app_path_namespaces_from_final_segment(tmp_path):
    """`apps.blog` registers under namespace `blog` — no path surgery involved."""
    base = tmp_path / "proj_dotted"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(
        '[spoc]\nmode = "development"\n\n[spoc.apps]\ndevelopment = ["apps.blog"]\n'
    )
    pkg = base / "apps" / "blog"
    pkg.mkdir(parents=True)
    (base / "apps" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "models.py").write_text(textwrap.dedent(MODELS_BODY))
    sys.path.insert(0, str(base))

    fw = Framework("models").start(base)
    assert [c.identifier for c in fw.registry] == ["models:blog.post"]


def test_app_named_like_stdlib_cannot_shadow_it(tmp_path):
    """A nested app whose final segment collides with the stdlib stays nested."""
    base = tmp_path / "proj_shadow"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(
        '[spoc]\nmode = "development"\n\n'
        '[spoc.apps]\ndevelopment = ["shadowpkg.logging"]\n'
    )
    pkg = base / "shadowpkg" / "logging"
    pkg.mkdir(parents=True)
    (base / "shadowpkg" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "models.py").write_text(textwrap.dedent(MODELS_BODY))
    sys.path.insert(0, str(base))

    fw = Framework("models").start(base)
    assert fw.resolve("models:logging.post")

    import logging

    assert hasattr(logging, "getLogger")  # the stdlib module, not the app


def test_unimportable_app_path_fails_naming_it(tmp_path):
    base = tmp_path / "proj_ghostapp"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(
        '[spoc]\nmode = "development"\n\n[spoc.apps]\ndevelopment = ["no.such.app"]\n'
    )
    fw = Framework("models")
    with pytest.raises(AppNotFoundError, match=r"no\.such\.app"):
        fw.start(base)
    assert fw.started is False


def test_app_final_segment_must_satisfy_the_grammar(tmp_path):
    base = tmp_path / "proj_badseg"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(
        '[spoc]\nmode = "development"\n\n[spoc.apps]\ndevelopment = ["apps.BadName"]\n'
    )
    with pytest.raises(InvalidSegmentError, match="BadName"):
        Framework("models").start(base)


def test_failed_start_leaves_the_framework_inert_and_retryable(tmp_path):
    """A failed boot must not strand half-booted state — fix the cause, start again."""
    base = make_project(tmp_path, "alpha")
    fw = Framework("models", "views")  # views is required and absent

    with pytest.raises(MissingModuleError):
        fw.start(base)

    assert fw.started is False
    assert fw.base_dir is None
    assert len(fw.registry) == 0

    (base / "alpha" / "views.py").write_text("")
    fw.start(base)
    assert fw.resolve("models:alpha.post")


def test_failed_startup_rolls_back_initialized_modules(tmp_path):
    """A module that fails to initialize must not strand its predecessors' teardown."""
    base = tmp_path / "proj_rollback"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(
        '[spoc]\nmode = "development"\n\n[spoc.apps]\ndevelopment = ["good", "bad"]\n'
    )
    modules = {
        "good": (
            "from pathlib import Path\n"
            "_here = Path(__file__).parent\n"
            "def initialize():\n"
            "    (_here / 'up.txt').write_text('up')\n"
            "def teardown():\n"
            "    (_here / 'down.txt').write_text('down')\n"
        ),
        "bad": "def initialize():\n    raise RuntimeError('boom')\n",
    }
    for app, body in modules.items():
        app_dir = base / app
        app_dir.mkdir(parents=True)
        (app_dir / "__init__.py").write_text("")
        (app_dir / "models.py").write_text(body)
    sys.path.insert(0, str(base))

    fw = Framework("models")
    with pytest.raises(RuntimeError, match="boom"):
        fw.start(base)

    assert (base / "good" / "up.txt").exists()
    assert (base / "good" / "down.txt").exists()
    assert fw.started is False


def test_kind_location_mismatch_fails_start(tmp_path):
    """A views component declared in models.py is a start error, not a drop."""
    base = make_project(
        tmp_path,
        "mismatch",
        """
        from spoc.core.declaration import component

        @component(kind="views")
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
        class Post:
            ...
        """,
    )
    (base / "fwdef.py").write_text(
        "import spoc\n"
        'framework = spoc.Framework("models")\n'
        'model = framework.kind("models")\n'
    )
    import fwdef

    fwdef.framework.start(base)
    assert [c.identifier for c in fwdef.framework.registry] == ["models:handleapp.post"]


def test_kind_dependency_order_across_modules(tmp_path):
    base = make_project(
        tmp_path,
        "ordered",
        MODELS_BODY
        + """
    def initialize():
        import fwtrace
        fwtrace.events.append("models")
    """,
        extra_modules={
            "views": (
                "def initialize():\n"
                "    import fwtrace\n"
                '    fwtrace.events.append("views")\n'
            )
        },
    )
    (base / "fwtrace.py").write_text("events = []\n")
    import fwtrace

    Framework("models", KindSpec("views", depends_on=("models",))).start(base)
    assert fwtrace.events == ["models", "views"]


# ── Per-kind optionality ──────────────────────────────────────────────────


def test_missing_required_module_fails_start(tmp_path):
    base = make_project(tmp_path, "reqapp")
    fw = Framework("models", "views")
    with pytest.raises(MissingModuleError) as exc:
        fw.start(base)
    message = str(exc.value)
    assert "reqapp" in message and "views" in message
    assert fw.started is False


def test_missing_optional_module_is_skipped(tmp_path):
    base = make_project(tmp_path, "optapp")
    fw = Framework("models", KindSpec("views", required=False)).start(base)
    assert fw.started is True
    assert [c.identifier for c in fw.registry] == ["models:optapp.post"]
    assert fw.registry.by_kind("views") == []


def test_optionality_does_not_leak_between_kinds(tmp_path):
    """One optional kind must not weaken the guarantee for a required one."""
    base = make_project(tmp_path, "mixedapp", models_body="")
    (base / "mixedapp" / "models.py").unlink()
    fw = Framework(KindSpec("views", required=False), "models")
    with pytest.raises(MissingModuleError) as exc:
        fw.start(base)
    message = str(exc.value)
    assert "models" in message
    assert "views" not in message


def test_broken_optional_module_is_still_an_error(tmp_path):
    """Absent and broken are different: a module that exists must import."""
    base = make_project(
        tmp_path,
        "brokenapp",
        extra_modules={"views": "import no_such_dependency\n"},
    )
    fw = Framework("models", KindSpec("views", required=False))
    with pytest.raises(ModuleNotFoundError) as exc:
        fw.start(base)
    assert exc.value.name == "no_such_dependency"


def test_required_is_the_default(tmp_path):
    assert KindSpec("views").required is True
    base = make_project(tmp_path, "defapp")
    with pytest.raises(MissingModuleError):
        Framework("models", "views").start(base)


# ── Typed per-kind metadata ───────────────────────────────────────────────


@dataclass(frozen=True)
class ModelMeta:
    table: str


def test_declared_metadata_reaches_the_record(tmp_path):
    base = make_project(
        tmp_path,
        "metaapp",
        """
        from dataclasses import dataclass
        from spoc.core.declaration import component

        @dataclass(frozen=True)
        class ModelMeta:
            table: str

        @component(kind="models", meta=ModelMeta(table="posts"))
        class Post:
            ...
        """,
    )
    fw = Framework(KindSpec("models", metadata=ModelMeta)).start(base)
    record = fw.resolve("models:metaapp.post")
    assert record.metadata.table == "posts"


def test_metadata_violating_the_contract_is_rejected():
    fw = Framework(KindSpec("models", metadata=ModelMeta))
    model = fw.kind("models")
    with pytest.raises(MetadataContractError):

        @model(meta={"table": "posts"})
        class Post: ...


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
    (base / "fwprobe.py").write_text("events = []\n")
    import fwprobe

    fw = Framework("models")

    @fw.on_ready
    def ready(registry):
        fwprobe.events.append("ready")

    fw.start(base)
    assert fwprobe.events == ["ready", "initialize"]


# ── Per-kind lifecycle hooks (declared on the KindSpec) ───────────────────


def test_hooks_receive_components_and_fire_in_order(tmp_path):
    base = make_project(tmp_path, "hookapp")
    seen: list[tuple[str, int]] = []

    fw = Framework(
        KindSpec(
            "models",
            on_startup=lambda objects: seen.append(("up", len(objects))),
            on_shutdown=lambda objects: seen.append(("down", len(objects))),
        )
    )
    fw.start(base)
    fw.shutdown()

    assert [tag for tag, _ in seen] == ["up", "down"]
    assert seen[0][1] == 1  # the one discovered Post
    assert fw.started is False


def test_hook_payload_is_an_ordered_immutable_tuple(tmp_path):
    """Hooks see the registry's canonical enumeration: identifier order, frozen."""
    base = make_project(
        tmp_path,
        "hookorder",
        """
    from spoc.core.declaration import component

    @component(kind="models")
    class Zeta: ...

    @component(kind="models")
    class Alpha: ...
    """,
    )
    payloads: list = []
    fw = Framework(KindSpec("models", on_startup=payloads.append))
    fw.start(base)
    fw.shutdown()
    fw.start(base)
    fw.shutdown()

    first, second = payloads
    assert isinstance(first, tuple)
    # Declared Zeta-first; identifier order puts alpha first, on every start.
    assert [obj.__name__ for obj in first] == ["Alpha", "Zeta"]
    assert [obj.__name__ for obj in second] == ["Alpha", "Zeta"]
    with pytest.raises(TypeError):
        first[0] = None


def test_app_initialize_error_propagates_and_rolls_back(tmp_path):
    """The error doctrine: an app's own failure surfaces unwrapped, after rollback."""
    base = make_project(
        tmp_path,
        "docterr",
        MODELS_BODY
        + """
    def initialize():
        raise ValueError("app boom")
    """,
    )
    fw = Framework("models")
    with pytest.raises(ValueError, match="app boom") as excinfo:
        fw.start(base)
    assert type(excinfo.value) is ValueError
    assert fw.started is False
    assert len(fw.registry) == 0  # rolled back to inert


def test_hooks_are_a_kind_attribute_not_a_second_surface():
    """Every per-kind attribute rides the KindSpec — there is no decorator form."""
    fw = Framework("models")
    assert not hasattr(fw, "on_startup")
    assert not hasattr(fw, "on_shutdown")


# ── Configuration behavior through start ──────────────────────────────────


def test_mode_cascade():
    apps = {
        "production": ["auth"],
        "staging": ["admin"],
        "development": ["demo"],
    }
    collect = Framework._collect_apps
    assert collect("development", apps, DEFAULT_MODES) == ["demo", "admin", "auth"]
    assert collect("staging", apps, DEFAULT_MODES) == ["admin", "auth"]
    assert collect("production", apps, DEFAULT_MODES) == ["auth"]


def test_unknown_mode_is_refused():
    """A mode typo must not silently install zero apps."""
    with pytest.raises(ConfigurationError, match="prod"):
        Framework._collect_apps("prod", {"development": ["demo"]}, DEFAULT_MODES)


def test_unknown_apps_group_is_refused():
    """An app list stranded under a misspelled mode is a defect, not dead config."""
    with pytest.raises(ConfigurationError, match="developmnet"):
        Framework._collect_apps("development", {"developmnet": ["demo"]}, DEFAULT_MODES)


def test_custom_mode_set_cascades_as_declared():
    modes = {**DEFAULT_MODES, "test": ["test", "production"]}
    apps = {"test": ["fixtures"], "production": ["auth"]}
    assert Framework._collect_apps("test", apps, modes) == ["fixtures", "auth"]


def test_cascade_entry_must_name_a_declared_mode():
    modes = {**DEFAULT_MODES, "test": ["test", "prod"]}
    with pytest.raises(ConfigurationError, match=r"spoc\.modes\.test"):
        Framework._collect_apps("test", {}, modes)


def test_declared_modes_merge_over_the_default_triple(tmp_path):
    """Adding `test` in config never forces restating dev/staging/prod, and
    an app declared under the custom mode boots through the whole stack."""
    base = make_project(
        tmp_path,
        "modeapp",
        extra_toml='\n[spoc.modes]\ntest = ["test", "development"]\n',
    )
    (base / "config" / "spoc.toml").write_text(
        (base / "config" / "spoc.toml")
        .read_text()
        .replace('mode = "development"', 'mode = "test"')
    )
    fw = Framework("models").start(base)
    # `test` cascades into development, whose app list holds the one app.
    assert [c.identifier for c in fw.registry] == ["models:modeapp.post"]
    fw.shutdown()


def test_mode_typo_fails_start_instead_of_booting_empty(tmp_path):
    base = tmp_path / "proj_modetypo"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(
        '[spoc]\nmode = "prod"\n\n[spoc.apps]\nproduction = ["demo"]\n'
    )
    with pytest.raises(ConfigurationError, match="prod"):
        Framework("models").start(base)


def test_error_message_carries_no_trailing_space():
    assert str(SpocError("Framework is already started")) == (
        "Framework is already started"
    )


def test_unresolvable_plugin_fails_start(tmp_path):
    base = make_project(
        tmp_path,
        "plugapp",
        extra_toml='\n[spoc.plugins]\nhooks = ["no_such_module.attr"]\n',
    )
    fw = Framework("models", KindSpec("hooks", required=False))
    with pytest.raises(AppNotFoundError, match="no_such_module"):
        fw.start(base)
    assert fw.started is False


def test_declared_plugin_registers_in_the_registry(tmp_path):
    """A plugin is a configured registration, not a second lookup surface."""
    base = make_project(
        tmp_path,
        "plugok",
        extra_toml='\n[spoc.plugins]\nhooks = ["plugok.extras.hook"]\n',
    )
    (base / "plugok" / "extras.py").write_text("def hook():\n    return 'loaded'\n")
    fw = Framework("models", KindSpec("hooks", required=False)).start(base)
    record = fw.resolve("hooks:plugok.hook")
    assert record.object() == "loaded"
    assert [c.identifier for c in fw.registry.by_kind("hooks")] == ["hooks:plugok.hook"]


def test_plugin_group_must_name_a_declared_kind(tmp_path):
    """The kind set is closed; a config file cannot widen it."""
    base = make_project(
        tmp_path,
        "plugbad",
        extra_toml='\n[spoc.plugins]\nhooks = ["plugbad.extras.hook"]\n',
    )
    fw = Framework("models")
    with pytest.raises(UnknownKindError, match="hooks"):
        fw.start(base)
    assert fw.started is False


def test_plugin_name_derives_from_the_attribute(tmp_path):
    """PEP 8 attribute names yield the conventional segment, as discovery does."""
    base = make_project(
        tmp_path,
        "plugcase",
        extra_toml='\n[spoc.plugins]\nhooks = ["plugcase.extras.AuditHook"]\n',
    )
    (base / "plugcase" / "extras.py").write_text("class AuditHook:\n    ...\n")
    fw = Framework("models", KindSpec("hooks", required=False)).start(base)
    assert fw.resolve("hooks:plugcase.audit_hook").name == "audit_hook"


def test_plugin_inside_dotted_app_path_takes_the_apps_namespace(tmp_path):
    """Discovery's grammar applied to the reference: the app segment, never the
    container package."""
    base = tmp_path / "proj_dotplug"
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(
        textwrap.dedent(
            """
            [spoc]
            mode = "development"

            [spoc.apps]
            development = ["apps.blog"]

            [spoc.plugins]
            hooks = ["apps.blog.extras.AuditHook"]
            """
        )
    )
    pkg = base / "apps" / "blog"
    pkg.mkdir(parents=True)
    (base / "apps" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "models.py").write_text(textwrap.dedent(MODELS_BODY))
    (pkg / "extras.py").write_text("class AuditHook:\n    ...\n")
    sys.path.insert(0, str(base))

    fw = Framework("models", KindSpec("hooks", required=False)).start(base)
    record = fw.resolve("hooks:blog.audit_hook")
    assert record.namespace == "blog"


def test_top_level_plugin_module_is_its_own_namespace(tmp_path):
    base = make_project(
        tmp_path,
        "plugtop",
        extra_toml='\n[spoc.plugins]\nhooks = ["plugmod.AuditHook"]\n',
    )
    (base / "plugmod.py").write_text("class AuditHook:\n    ...\n")
    fw = Framework("models", KindSpec("hooks", required=False)).start(base)
    assert fw.resolve("hooks:plugmod.audit_hook").namespace == "plugmod"


# ── Independence and removed API ──────────────────────────────────────────


def test_two_frameworks_are_independent(tmp_path):
    """De-globalized composition: registries, handles, hooks never leak."""
    base_a = make_project(
        tmp_path,
        "alpha",
        """
        from spoc.core.declaration import component

        @component(kind="models")
        class Post:
            ...
        """,
    )
    base_b = make_project(
        tmp_path,
        "beta",
        """
        from spoc.core.declaration import component

        @component(kind="models")
        class Order:
            ...
        """,
    )
    hooks_seen: list[str] = []
    fw_a = Framework("models")
    fw_b = Framework(KindSpec("models", on_startup=lambda o: hooks_seen.append("b")))

    fw_a.start(base_a)
    fw_b.start(base_b)

    assert [c.identifier for c in fw_a.registry] == ["models:alpha.post"]
    assert [c.identifier for c in fw_b.registry] == ["models:beta.order"]
    assert fw_a.loader is not fw_b.loader
    assert fw_a.registry is not fw_b.registry
    # fw_b's hook ran for fw_b only
    assert hooks_seen == ["b"]
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
        "Importer",
        "component",
        "case_style",
        "inject_apps",
    ):
        assert not hasattr(spoc, gone), gone
    fw = Framework("models")
    assert not hasattr(fw, "get_component")
    assert not hasattr(fw, "importer")
    assert not hasattr(type(fw), "components")


def test_framework_wide_strict_loose_switch_is_gone():
    """Optionality is per kind; the global switch was deleted, not deprecated."""
    with pytest.raises(TypeError):
        Framework("models", mode="loose")  # ty: ignore[unknown-argument]
    assert not hasattr(Framework("models"), "mode")
