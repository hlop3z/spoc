"""
The registry projected as data: one test per spec scenario in
`registry-projection`, plus the containment boundary and the schema contract.

The suite is also the drift control for a hand-written schema. Every projection
built here is validated against the published file, and a parity test holds the
producer's field set to the schema's — so the two descriptions of one document
cannot diverge silently, which is the cost the build-vs-adopt ADR accepted when
it chose authorship over generation.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.protocols import Validator

import spoc
from spoc.cli import main as cli_main
from spoc.projection import (
    FORMAT_VERSION,
    ComponentEntry,
    Projection,
    dumps,
    project,
    schema_path,
    schema_text,
)
from spoc.projection.produce import collected
from spoc.testing import ProjectTree

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")

CATALOG_MODELS = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Product:
        price_cents = 2900
"""

CATALOG_VIEWS = """
    from spoc.core.declaration import component

    @component(kind="views")
    def list_products() -> dict[str, int]:
        return {"count": 1}
"""

CATALOG_RESOURCES = """
    from spoc.core.declaration import component

    class SearchIndex:
        def lookup(self, term: str) -> str:
            return term

    index = component(SearchIndex(), kind="resources", name="index")
"""

FRAMEWORK = """
    import spoc

    framework = spoc.Framework(
        spoc.KindSpec("models", required=False),
        spoc.KindSpec("views", depends_on=("models",), required=False),
        spoc.KindSpec("resources", required=False),
        spoc.KindSpec("reports", required=False),
    )
"""


def project_tree(
    tmp_path: Path, *, name: str = "proj", installed: list[str] | None = None
) -> Path:
    """A project covering all three shapes, plus a declared-but-empty kind."""
    apps = {
        "catalog": {
            "models": CATALOG_MODELS,
            "views": CATALOG_VIEWS,
            "resources": CATALOG_RESOURCES,
        }
    }
    config = {"apps": {"development": installed or ["catalog"]}}
    base = ProjectTree(apps=apps, config=config).build(tmp_path, name)
    (base / "framework.py").write_text(textwrap.dedent(FRAMEWORK), encoding="utf-8")
    return base


def validator() -> Validator:
    """The published schema, checked for validity before it checks anything."""
    schema = json.loads(schema_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validated(projection: Projection) -> dict:
    """Round-trip a projection through its document text, validating it."""
    document = json.loads(dumps(projection))
    validator().validate(document)
    return document


# ── Content: every component once, and the declared kind set ──────────────


def test_every_component_appears_exactly_once(tmp_path):
    base = project_tree(tmp_path)

    document = validated(project(base))

    identifiers = [entry["identifier"] for entry in document["components"]]
    assert identifiers == [
        "models:catalog.product",
        "resources:catalog.index",
        "views:catalog.list_products",
    ]
    assert len(identifiers) == len(set(identifiers))


def test_an_entry_states_the_facets_the_location_and_the_shape(tmp_path):
    base = project_tree(tmp_path)

    document = validated(project(base))

    entry = next(
        e for e in document["components"] if e["identifier"] == "models:catalog.product"
    )
    assert entry == {
        "identifier": "models:catalog.product",
        "kind": "models",
        "namespace": "catalog",
        "object_name": "product",
        "location": "catalog.models:Product",
        "shape": "constructible",
    }


def test_the_declared_kind_set_includes_a_kind_with_no_components(tmp_path):
    """'Declared and empty' and 'never declared' are different facts."""
    base = project_tree(tmp_path)

    document = validated(project(base))

    assert document["kinds"] == ["models", "views", "resources", "reports"]
    assert "reports" not in {e["kind"] for e in document["components"]}


def test_the_three_shapes_are_distinguished(tmp_path):
    base = project_tree(tmp_path)

    shapes = {
        entry["identifier"]: entry["shape"]
        for entry in validated(project(base))["components"]
    }

    assert shapes["models:catalog.product"] == "constructible"
    assert shapes["views:catalog.list_products"] == "callable"
    assert shapes["resources:catalog.index"] == "value"


def test_the_projection_carries_no_python_type_reference(tmp_path):
    """Language-specific detail stays in the stub; see design Decision 3."""
    base = project_tree(tmp_path)

    document = validated(project(base))

    assert "type_ref" not in json.dumps(document)
    for entry in document["components"]:
        assert set(entry) == {
            "identifier",
            "kind",
            "namespace",
            "object_name",
            "location",
            "shape",
        }


# ── Ordering: canonical, and independent of how the project is declared ───


def test_a_registered_instance_is_located_by_its_type(tmp_path):
    """An instance is constructed, not defined, and its repr carries a memory
    address — so locating it by repr would make two projections differ."""
    base = project_tree(tmp_path)

    document = validated(project(base))

    entry = next(
        e
        for e in document["components"]
        if e["identifier"] == "resources:catalog.index"
    )
    assert entry["location"] == "catalog.resources:SearchIndex"
    assert "0x" not in entry["location"]


def test_two_projections_of_one_registry_are_byte_identical(tmp_path):
    base = project_tree(tmp_path)

    first = dumps(project(base))
    second = dumps(project(base))

    assert first == second


def test_reordering_the_installed_apps_leaves_the_projection_unchanged(tmp_path):
    apps: dict[str, dict[str, str]] = {
        "catalog": {"models": CATALOG_MODELS},
        "shop": {"models": CATALOG_MODELS.replace("Product", "Order")},
    }

    forward = ProjectTree(
        apps=apps, config={"apps": {"development": ["catalog", "shop"]}}
    ).build(tmp_path, "forward")
    reverse = ProjectTree(
        apps=apps, config={"apps": {"development": ["shop", "catalog"]}}
    ).build(tmp_path, "reverse")
    for base in (forward, reverse):
        (base / "framework.py").write_text(textwrap.dedent(FRAMEWORK), encoding="utf-8")

    assert dumps(project(forward)) == dumps(project(reverse))


# ── Boot depth: discovery only ────────────────────────────────────────────


def test_a_project_whose_startup_would_fail_is_still_describable(tmp_path):
    """The property that makes the projection usable in CI and in editors."""
    base = project_tree(tmp_path)
    (base / "catalog" / "models.py").write_text(
        textwrap.dedent(CATALOG_MODELS)
        + textwrap.dedent(
            """
            def on_startup(components):
                raise RuntimeError("no database on this machine")
            """
        ),
        encoding="utf-8",
    )

    document = validated(project(base))

    assert "models:catalog.product" in {e["identifier"] for e in document["components"]}


def test_ready_callback_registrations_are_included(tmp_path):
    """Ready callbacks complete within discovery, so they are in scope."""
    base = project_tree(tmp_path)
    (base / "framework.py").write_text(
        textwrap.dedent(FRAMEWORK)
        + textwrap.dedent(
            """
            @framework.on_ready
            def _register_extra(registry):
                registry.add("reports", "catalog", "summary", lambda: None)
            """
        ),
        encoding="utf-8",
    )

    document = validated(project(base))

    assert "reports:catalog.summary" in {
        e["identifier"] for e in document["components"]
    }


def test_a_discovery_failure_is_still_a_failure(tmp_path):
    base = project_tree(tmp_path, installed=["catalog", "missing"])

    with pytest.raises(spoc.SpocError) as exc:
        project(base)

    assert "missing" in str(exc.value)


def test_projection_leaves_no_residue(tmp_path):
    base = project_tree(tmp_path)
    path_before, modules_before = list(sys.path), set(sys.modules)

    project(base)

    assert sys.path == path_before
    assert set(sys.modules) == modules_before


# ── The schema ────────────────────────────────────────────────────────────


def test_the_published_schema_is_a_valid_2020_12_schema():
    schema = json.loads(schema_text())

    Draft202012Validator.check_schema(schema)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_the_schema_ships_beside_the_package():
    assert schema_path().is_file()
    assert schema_path().parent.name == "projection"


def test_a_document_missing_a_required_field_fails_validation(tmp_path):
    base = project_tree(tmp_path)
    document = json.loads(dumps(project(base)))
    del document["components"][0]["shape"]

    errors = list(validator().iter_errors(document))

    assert errors and "shape" in errors[0].message


def test_a_shape_outside_the_vocabulary_fails_validation(tmp_path):
    base = project_tree(tmp_path)
    document = json.loads(dumps(project(base)))
    document["components"][0]["shape"] = "module"

    errors = list(validator().iter_errors(document))

    assert errors and "module" in errors[0].message


def test_the_format_version_is_stated_and_is_not_the_release_version(tmp_path):
    base = project_tree(tmp_path)

    document = validated(project(base))

    assert document["format_version"] == FORMAT_VERSION
    assert document["format_version"] != spoc.__version__


def test_the_schema_and_the_producer_describe_the_same_fields():
    """The parity check the hand-written schema is paid for with.

    A field added to the producer and not to the schema — or the reverse —
    fails here rather than in whatever consumer reads the document next.
    """
    schema = json.loads(schema_text())

    document_fields = set(Projection.__dataclass_fields__)
    entry_fields = set(ComponentEntry.__dataclass_fields__)

    assert document_fields == set(schema["properties"]) == set(schema["required"])
    component = schema["$defs"]["component"]
    assert entry_fields == set(component["properties"]) == set(component["required"])


# ── The command ───────────────────────────────────────────────────────────


def test_the_command_and_the_library_yield_the_same_document(tmp_path, capsys):
    base = project_tree(tmp_path)

    assert cli_main(["projection", str(base)]) == 0

    assert capsys.readouterr().out == dumps(project(base))


def test_the_command_writes_only_the_document_to_standard_output(tmp_path, capsys):
    base = project_tree(tmp_path)

    cli_main(["projection", str(base)])

    captured = capsys.readouterr()
    validator().validate(json.loads(captured.out))
    assert captured.err == ""


def test_a_command_failure_uses_the_existing_exit_code_contract(tmp_path, capsys):
    base = project_tree(tmp_path, installed=["missing"])

    assert cli_main(["projection", str(base)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ")


# ── Boundaries ────────────────────────────────────────────────────────────


def test_no_kernel_module_imports_the_projection():
    """Same contract as formats/scaffold/stubs: the boundary holds in source.

    The projection depends inward on the kernel and is depended on by the two
    surfaces that describe a registry — `spoc.stubs` and `spoc.diagnostics`.
    Nothing in the kernel may depend back on it.
    """
    root = Path(__file__).parent.parent / "src/spoc"
    for path in sorted(root.rglob("*.py")):
        if (
            (root / "projection") in path.parents
            or (root / "diagnostics") in path.parents
            or (root / "stubs") in path.parents
            or path == root / "cli.py"
        ):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            else:
                continue
            for name in names:
                assert "projection" not in name.split("."), f"{path.name}: {name}"


def test_importing_spoc_never_loads_the_projection():
    code = "import sys, spoc; print([m for m in sys.modules if 'spoc.projection' in m])"

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "[]"


def test_the_projection_serializes_through_the_standard_library():
    """The containment boundary: `spoc.formats` is an optional-extra subpackage
    and a core surface must not become load-bearing on it."""
    root = Path(__file__).parent.parent / "src/spoc/projection"
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            else:
                continue
            for name in names:
                assert "formats" not in name.split("."), f"{path.name}: {name}"

    assert "import json" in (root / "document.py").read_text(encoding="utf-8")


# ── The describing boot holds the transition gate ─────────────────────────


def _located(base: Path) -> spoc.Framework:
    """The project's framework, imported the way every describing surface does."""
    from spoc.locate import locate_framework

    sys.path.insert(0, str(base))
    return locate_framework()


def test_describing_a_started_framework_is_refused(tmp_path):
    base = project_tree(tmp_path)
    fw = _located(base)
    fw.start(base)
    try:
        with (
            pytest.raises(spoc.SpocError, match="started framework"),
            collected(fw, base),
        ):
            pass  # pragma: no cover - the refusal precedes the yield
    finally:
        fw.shutdown()


def test_lifecycle_call_from_inside_a_description_is_reentrancy(tmp_path):
    """The describing boot is a transition: starting the framework from within
    it is refused as reentrancy, never deadlocked on the gate's own lock."""
    base = project_tree(tmp_path)
    fw = _located(base)
    with (
        collected(fw, base),
        pytest.raises(spoc.SpocError, match="inside a lifecycle transition"),
    ):
        fw.start(base)


def test_read_racing_a_description_names_the_transition(tmp_path):
    """A resolve arriving from another thread mid-description gets the gate's
    timing error naming describe() — not a typo report, not a torn record."""
    base = project_tree(tmp_path)
    fw = _located(base)
    outcomes: list[BaseException | str] = []

    def read():
        try:
            fw.resolve("models:catalog.product")
            outcomes.append("resolved")
        except BaseException as caught:
            outcomes.append(caught)

    with collected(fw, base):
        reader = threading.Thread(target=read)
        reader.start()
        reader.join(timeout=10)
        assert not reader.is_alive(), "racing read never returned"

    assert len(outcomes) == 1
    (outcome,) = outcomes
    assert isinstance(outcome, spoc.FrameworkTransitioningError)
    assert "describe()" in str(outcome)


def test_start_racing_a_description_serializes_after_it(tmp_path):
    """A sync start launched mid-description waits for the gate and then boots
    cleanly — the two half-boots never interleave."""
    base = project_tree(tmp_path)
    fw = _located(base)
    started: list[bool] = []

    def boot():
        fw.start(base)
        started.append(fw.started)

    with collected(fw, base):
        racer = threading.Thread(target=boot)
        racer.start()
        # The starter must still be waiting while the description is open.
        racer.join(timeout=0.2)
        assert racer.is_alive(), "start() proceeded during an open description"

    racer.join(timeout=10)
    assert not racer.is_alive(), "start() never acquired the gate"
    try:
        assert started == [True]
    finally:
        fw.shutdown()
