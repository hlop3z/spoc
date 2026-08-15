"""
Stub generation: the describe pass, the emitter, the CLI, and the runtime
inertness that makes the whole approach viable — one test per spec scenario in
typed-registry-stubs, plus the containment boundary.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal, TypeVar
from unittest import mock

import pytest

from spoc import stubs
from spoc.cli import main as cli_main
from spoc.projection import project as projection
from spoc.stubs import (
    NARROWING_LIMIT,
    StubReport,
    UnmirrorableRootError,
    alias_for,
    generate,
    reference_for,
    render,
    verify,
)
from spoc.testing import ProjectTree

# ── Fixtures: a project with all three shapes, a plugin, and a degraded entry ──

CATALOG_MODELS = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Product:
        price_cents = 2900
"""

CATALOG_VIEWS = """
    from spoc.core.declaration import component

    EFFECTS = []

    @component(kind="views")
    def list_products() -> dict[str, int]:
        return {"count": 1}

    @component(kind="views")
    def untyped(a, b=2, *rest):
        return None

    def initialize():
        EFFECTS.append("initialized")

    def teardown():
        EFFECTS.append("torn down")
"""

CATALOG_RESOURCES = """
    from spoc.core.declaration import component

    class SearchIndex:
        def lookup(self, term: str) -> str:
            return term

    index = component(SearchIndex(), kind="resources", name="index")
"""

PLUGIN_MODULE = """
    class Cache:
        def get(self, key: str) -> str:
            return key

    shared_cache = Cache()
"""

FRAMEWORK = """
    import spoc

    framework = spoc.Framework(
        spoc.KindSpec("models", required=False),
        spoc.KindSpec("views", depends_on=("models",), required=False),
        spoc.KindSpec("resources", required=False),
        spoc.KindSpec("caches", required=False),
    )
    model = framework.kind("models")
    view = framework.kind("views")
"""


def project(tmp_path: Path, *, framework_body: str = FRAMEWORK, **extra) -> Path:
    """A project exercising every shape the emitter has to render."""
    apps = {
        "catalog": {
            "models": CATALOG_MODELS,
            "views": CATALOG_VIEWS,
            "resources": CATALOG_RESOURCES,
            "plugins_home": PLUGIN_MODULE,
        }
    }
    config = {
        "apps": {"development": ["catalog"]},
        "plugins": {"caches": ["catalog.plugins_home.shared_cache"]},
        **extra,
    }
    base = ProjectTree(apps=apps, config=config).build(tmp_path, "proj")
    (base / "framework.py").write_text(
        textwrap.dedent(framework_body), encoding="utf-8"
    )
    return base


# ── Containment ───────────────────────────────────────────────────────────


def test_no_kernel_module_imports_the_stub_generator():
    """Same contract as formats/scaffold/diagnostics: it holds in source."""
    root = Path(__file__).parent.parent / "src/spoc"
    for path in sorted(root.rglob("*.py")):
        if (root / "stubs") in path.parents or path == root / "cli.py":
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
                assert "stubs" not in name.split("."), f"{path.name}: {name}"


def test_importing_spoc_never_loads_the_stub_generator():
    code = "import sys, spoc; print([m for m in sys.modules if 'spoc.stubs' in m])"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


# ── Describing does not run the project ───────────────────────────────────


def test_initializers_do_not_run_during_description(tmp_path):
    base = project(tmp_path)
    _, text, manifest = render(base)
    assert manifest.entries
    # The module's initialize() appends to EFFECTS; describing must not.
    assert "initialized" not in text


def test_description_leaves_no_residue(tmp_path):
    base = project(tmp_path)
    path_before, modules_before = list(sys.path), set(sys.modules)

    render(base)

    assert sys.path == path_before
    assert set(sys.modules) == modules_before


def test_description_can_be_repeated_and_then_booted(tmp_path):
    base = project(tmp_path)
    render(base)
    render(base)
    result = _run_in_project(
        base, "framework.start(BASE); print(len(framework.registry))"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("5")


# ── Coverage of the resolution surface ────────────────────────────────────


def test_every_registered_identifier_appears(tmp_path):
    base = project(tmp_path)
    _, _, manifest = render(base)
    assert {entry.identifier for entry in manifest.entries} == {
        "caches:catalog.shared_cache",
        "models:catalog.product",
        "resources:catalog.index",
        "views:catalog.list_products",
        "views:catalog.untyped",
    }


def test_the_stub_and_the_projection_agree(tmp_path):
    """The stub derives from the projection, so the two descriptions of one
    registry cover the same identifiers in the same order by construction."""
    base = project(tmp_path)
    _, _, manifest = render(base)

    projected = projection(base)

    assert [entry.identifier for entry in manifest.entries] == [
        component.identifier for component in projected.components
    ]
    assert manifest.kinds == projected.kinds


def test_the_stub_carries_a_type_the_projection_does_not(tmp_path):
    """Language-specific detail belongs to the description, not the format."""
    base = project(tmp_path)
    _, _, manifest = render(base)

    entry = next(
        e for e in manifest.entries if e.identifier == "models:catalog.product"
    )

    assert entry.type_ref.expression.startswith("type[")
    assert not hasattr(entry.component, "type_ref")


def test_configuration_registered_components_appear(tmp_path):
    """A [spoc.plugins] entry exists only after config resolves — the case a
    static extractor could not see."""
    base = project(tmp_path)
    _, text, manifest = render(base)
    identifiers = {entry.identifier for entry in manifest.entries}
    assert "caches:catalog.shared_cache" in identifiers
    assert "caches:catalog.shared_cache" in text


def test_the_three_shapes_are_distinguished(tmp_path):
    base = project(tmp_path)
    _, _, manifest = render(base)
    shapes = {entry.identifier: entry.shape for entry in manifest.entries}
    assert shapes["models:catalog.product"] == "constructible"
    assert shapes["views:catalog.list_products"] == "callable"
    assert shapes["resources:catalog.index"] == "value"
    assert shapes["caches:catalog.shared_cache"] == "value"


def test_a_class_renders_as_its_constructor(tmp_path):
    base = project(tmp_path)
    _, text, _ = render(base)
    assert "type[_catalog_models_Product]" in text


def test_a_callable_renders_its_signature(tmp_path):
    base = project(tmp_path)
    _, text, _ = render(base)
    assert "[[], dict[str, int]]" in text


def test_a_value_renders_its_own_type(tmp_path):
    base = project(tmp_path)
    _, text, _ = render(base)
    assert "Component[_catalog_resources_SearchIndex]" in text


# ── Degradation is honest and counted ─────────────────────────────────────


def test_unannotated_callable_degrades_without_guessing(tmp_path):
    base = project(tmp_path)
    _, _, manifest = render(base)
    degraded = [e for e in manifest.entries if e.type_ref.degraded]
    assert [e.identifier for e in degraded] == ["views:catalog.untyped"]
    assert degraded[0].type_ref.expression.endswith("[..., Any]")


def test_degraded_entries_are_still_present_and_counted(tmp_path):
    base = project(tmp_path)
    _, text, manifest = render(base)
    assert manifest.degraded == 1
    assert "views:catalog.untyped" in text


# ── Determinism ───────────────────────────────────────────────────────────


def test_repeated_generation_is_byte_identical(tmp_path):
    base = project(tmp_path)
    first = render(base)[1]
    second = render(base)[1]
    assert first == second


def test_declaration_order_does_not_change_the_output(tmp_path):
    """Two projects registering the same components in different source order
    describe identically — order is the grammar's, not the file's."""
    reordered = CATALOG_MODELS.replace("Product", "Product")
    one = project(tmp_path / "a")
    two_apps = {
        "catalog": {
            "models": reordered,
            "resources": CATALOG_RESOURCES,
            "views": CATALOG_VIEWS,
            "plugins_home": PLUGIN_MODULE,
        }
    }
    base_two = ProjectTree(
        apps=two_apps,
        config={
            "apps": {"development": ["catalog"]},
            "plugins": {"caches": ["catalog.plugins_home.shared_cache"]},
        },
    ).build(tmp_path / "b", "proj")
    (base_two / "framework.py").write_text(textwrap.dedent(FRAMEWORK), encoding="utf-8")
    assert render(one)[1] == render(base_two)[1]


# ── Strict mode ───────────────────────────────────────────────────────────


def test_permissive_keeps_the_catch_all_overload(tmp_path):
    base = project(tmp_path)
    _, text, _ = render(base)
    assert "def resolve(self, identifier: str) -> Component[Any]: ..." in text


def test_strict_omits_the_catch_all_overload(tmp_path):
    base = project(tmp_path)
    _, text, _ = render(base, strict=True)
    assert "identifier: str) -> Component[Any]" not in text


def test_strict_pins_its_suppression_where_mypy_anchors(tmp_path):
    """mypy reads `[override]` suppressions on the first `@overload` decorator
    line, not the `def` below it — the mis-anchored comment is exactly how a
    strict stub shipped failing mypy. And no pyright suppression: pyright
    reports nothing for this narrowing, and a comment no checker reads is a
    claim the conformance gate cannot verify (worse, pyright flags unused
    ignores under reportUnnecessaryTypeIgnoreComment)."""
    base = project(tmp_path)
    _, text, _ = render(base, strict=True)
    assert "@overload  # type: ignore[override]" in text
    assert text.count("type: ignore[override]") == 1
    assert "pyright: ignore" not in text


def test_strict_single_entry_pins_the_suppression_to_the_def_line(tmp_path):
    """With one component there is no `@overload` line, and a comment trailing
    a long one-line signature gets carried onto the `...` line by the
    formatter, where mypy never reads it. The signature is emitted pre-broken
    so the comment stays on the `def` line, which mypy honors there."""
    apps = {"solo": {"models": CATALOG_MODELS}}
    base = ProjectTree(apps=apps, config={"apps": {"development": ["solo"]}}).build(
        tmp_path, "proj"
    )
    (base / "framework.py").write_text(textwrap.dedent(FRAMEWORK), encoding="utf-8")

    _, text, _ = render(base, strict=True)
    assert "def resolve(  # type: ignore[override]" in text
    assert "    @overload" not in text


# ── Navigation surface ────────────────────────────────────────────────────


def test_navigation_renders_nested_members_per_grammar_segment(tmp_path):
    base = project(tmp_path)
    _, text, _ = render(base)

    assert "class _ns_models_catalog:" in text
    assert "    product: Component[type[_catalog_models_Product]]" in text
    assert "class _kind_models:" in text
    assert "    catalog: _ns_models_catalog" in text
    assert "class _Objects:" in text
    assert "    models: _kind_models" in text
    assert "    def objects(self) -> _Objects: ..." in text


def test_navigation_covers_exactly_the_registered_identifiers(tmp_path):
    """The tree and the overloads describe one registry; neither may carry a
    component the other does not."""
    base = project(tmp_path)
    _, _, manifest = render(base)

    navigated = {
        f"{kind}:{namespace}.{entry.object_name}"
        for kind, namespaces in manifest.navigation.items()
        for namespace, entries in namespaces.items()
        for entry in entries
    }
    assert navigated == {entry.identifier for entry in manifest.entries}


def test_navigation_is_identical_in_both_modes(tmp_path):
    """Strict withholds an overload; it has nothing to withhold from the tree,
    where an undeclared member is an error by absence."""
    base = project(tmp_path)
    permissive = render(base)[1]
    strict = render(base, strict=True)[1]

    def tree(text: str) -> str:
        return text.split("class _Root(Framework):")[0]

    assert tree(permissive) == tree(strict)


def test_navigation_escapes_a_reserved_word_segment(tmp_path):
    """`class` is not spellable as a member; `class_` is — and the identifier
    the overload narrows on keeps the unescaped name."""
    models = """
        from spoc.core.declaration import component

        @component(kind="class")
        class Seminar:
            pass
    """
    framework_body = """
        import spoc

        framework = spoc.Framework(spoc.KindSpec("class", required=False))
    """
    apps = {"school": {"class": textwrap.dedent(models)}}
    base = ProjectTree(apps=apps, config={"apps": {"development": ["school"]}}).build(
        tmp_path, "proj"
    )
    (base / "framework.py").write_text(
        textwrap.dedent(framework_body), encoding="utf-8"
    )

    _, text, _ = render(base)

    assert "    class_: _kind_class" in text
    assert '"class:school.seminar"' in text


def test_an_empty_project_still_offers_the_navigation_root(tmp_path):
    """A project that has registered nothing yet must say "no members", not
    "unknown attribute"."""
    framework_body = """
        import spoc

        framework = spoc.Framework(spoc.KindSpec("models", required=False))
    """
    base = ProjectTree(apps={}, config={"apps": {"development": []}}).build(
        tmp_path, "proj"
    )
    (base / "framework.py").write_text(
        textwrap.dedent(framework_body), encoding="utf-8"
    )

    _, text, _ = render(base)

    assert "class _Objects:" in text
    assert "    def objects(self) -> _Objects: ..." in text


# ── Size guard ────────────────────────────────────────────────────────────


def test_a_registry_within_the_limit_reports_nothing(tmp_path):
    base = project(tmp_path)
    report = generate(base)
    assert report.entries <= NARROWING_LIMIT
    assert report.oversized is None


def test_the_guard_names_the_count_threshold_and_alternative():
    """The report is composed on the report object, so every surface renders
    one sentence rather than writing its own."""
    oversized = StubReport(
        path=Path("framework.pyi"), entries=NARROWING_LIMIT + 1, degraded=0
    )
    message = oversized.oversized or ""
    assert str(NARROWING_LIMIT + 1) in message
    assert str(NARROWING_LIMIT) in message
    assert "framework.objects" in message
    assert "still written" in message


def test_the_guard_does_not_change_the_emitted_bytes(tmp_path):
    """Below or above the threshold, the stub is the same artifact — the guard
    informs a decision, it does not make one."""
    base = project(tmp_path)
    _, text, manifest = render(base)
    assert len(manifest.entries) <= NARROWING_LIMIT

    with mock.patch.object(stubs, "NARROWING_LIMIT", 1):
        report = generate(base)
        assert report.oversized is not None
        assert report.path.read_text(encoding="utf-8") == text


def test_the_cli_reports_the_guard_without_failing(tmp_path, capsys):
    with mock.patch.object(stubs, "NARROWING_LIMIT", 1):
        code = cli_main(["stubs", str(project(tmp_path))])
    captured = capsys.readouterr()
    assert code == 0
    assert "wrote" in captured.out
    assert "framework.objects" in captured.err


# ── The composition root must be mirrorable ───────────────────────────────


def test_unmirrorable_root_is_refused_by_name(tmp_path):
    base = project(
        tmp_path,
        framework_body=FRAMEWORK + "\n    def helper():\n        return 1\n",
    )
    with pytest.raises(UnmirrorableRootError) as exc:
        render(base)
    assert "helper" in str(exc.value)


def test_kind_handles_are_mirrored(tmp_path):
    base = project(tmp_path)
    _, text, manifest = render(base)
    assert {handle.attribute for handle in manifest.handles} == {"model", "view"}
    # Typed as the handle itself, not as a bare callable: a handle preserves
    # the type of what it decorates, and `Callable[..., Any]` would erase every
    # decorated class at its declaration site.
    assert "model: KindHandle" in text


# ── The emitted stub survives the project's own gates ─────────────────────


def test_generated_stub_lints_and_formats_clean(tmp_path):
    base = project(tmp_path)
    report = generate(base)
    lint = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--isolated",
            "--select",
            "I,F,PYI,E4,E7,E9,UP,B,SIM,RUF",
            str(report.path),
        ],
        capture_output=True,
        text=True,
    )
    assert lint.returncode == 0, lint.stdout
    fmt = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--isolated",
            "--check",
            str(report.path),
        ],
        capture_output=True,
        text=True,
    )
    assert fmt.returncode == 0, fmt.stdout


# ── Verification ──────────────────────────────────────────────────────────


def test_current_stub_verifies_and_is_untouched(tmp_path):
    base = project(tmp_path)
    report = generate(base)
    before = report.path.read_bytes()

    result = verify(base)

    assert result.ok and result.matched is True
    assert report.path.read_bytes() == before


def test_strict_stub_verifies_under_the_strict_flag(tmp_path):
    """`spoc stubs --check --strict` must give a committed strict stub the same
    staleness detection the permissive path gets — and the modes must not be
    confusable: a stub from one mode is stale under the other mode's check."""
    base = project(tmp_path)
    generate(base, strict=True)

    assert verify(base, strict=True).matched is True
    assert verify(base).matched is False


def test_added_component_is_a_mismatch(tmp_path):
    base = project(tmp_path)
    generate(base)
    before = (base / "framework.pyi").read_bytes()

    models = base / "catalog" / "models.py"
    models.write_text(
        models.read_text(encoding="utf-8")
        + '\n@component(kind="models")\nclass Invoice:\n    total = 1\n',
        encoding="utf-8",
    )

    result = verify(base)
    assert not result.ok
    assert "stale" in (result.reason or "") or "missing" in (result.reason or "")
    assert (base / "framework.pyi").read_bytes() == before


def test_missing_stub_is_a_mismatch_not_a_pass(tmp_path):
    base = project(tmp_path)
    result = verify(base)
    assert not result.ok
    assert "no stub" in (result.reason or "")
    assert not (base / "framework.pyi").exists()


def test_formatting_trivial_difference_is_not_stale(tmp_path):
    """Staleness is a claim about content, not about a formatter's opinion.

    A stored stub perturbed in a way ruff format undoes — here, extra blank
    lines at the end — must still verify: byte-comparing unformatted texts
    made a ruff upgrade between generation and verification report every stub
    stale with no content difference at all. Relies on ruff being importable,
    the same dependency test_generated_stub_lints_and_formats_clean shells to.
    """
    base = project(tmp_path)
    report = generate(base)
    stored = report.path.read_text(encoding="utf-8")
    report.path.write_text(stored + "\n\n", encoding="utf-8", newline="\n")

    assert verify(base).matched is True


def test_format_passes_text_through_on_timeout(monkeypatch):
    """A wedged formatter degrades to pass-through, never a hang or a crash."""
    from spoc import stubs

    def wedged(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ruff", timeout=stubs._FORMAT_TIMEOUT)

    monkeypatch.setattr(subprocess, "run", wedged)
    assert stubs._format("x: int\n") == "x: int\n"


# ── CLI adapter ───────────────────────────────────────────────────────────


def test_cli_generates_and_reports_degraded_count(tmp_path, capsys):
    base = project(tmp_path)
    code = cli_main(["stubs", str(base)])
    out = capsys.readouterr().out
    assert code == 0
    assert "framework.pyi" in out
    assert "1 of 5" in out


def test_cli_check_passes_on_a_current_stub(tmp_path, capsys):
    base = project(tmp_path)
    cli_main(["stubs", str(base)])
    capsys.readouterr()
    assert cli_main(["stubs", str(base), "--check"]) == 0
    assert "is current" in capsys.readouterr().out


def test_cli_check_fails_when_no_stub_exists(tmp_path, capsys):
    base = project(tmp_path)
    assert cli_main(["stubs", str(base), "--check"]) == 1
    assert "no stub" in capsys.readouterr().err


# ── Runtime inertness ─────────────────────────────────────────────────────


def _run_in_project(base: Path, body: str) -> subprocess.CompletedProcess[str]:
    script = (
        f"import sys; sys.path.insert(0, r'{base}')\n"
        f"BASE = r'{base}'\n"
        "from framework import framework\n" + body + "\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(base),
    )


def test_generated_stub_is_never_imported_at_runtime(tmp_path):
    base = project(tmp_path)
    generate(base)
    result = _run_in_project(
        base,
        "framework.start(BASE)\n"
        "import sys\n"
        "print(any(getattr(m, '__file__', '') or '' "
        "for n, m in sys.modules.items() if n.endswith('.pyi')))",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("False")


def test_deleting_the_stub_changes_no_behavior(tmp_path):
    base = project(tmp_path)
    generate(base)
    body = (
        "framework.start(BASE); print(sorted(c.identifier for c in framework.registry))"
    )

    with_stub = _run_in_project(base, body)
    (base / "framework.pyi").unlink()
    without_stub = _run_in_project(base, body)

    assert with_stub.returncode == 0, with_stub.stderr
    assert without_stub.returncode == 0, without_stub.stderr
    assert with_stub.stdout == without_stub.stdout


# ── Rendering one annotation at a time ────────────────────────────────────
#
# Everything above reaches the renderer through a generated project, so it sees
# only the annotations those fixtures happen to use. These call `reference_for`
# directly, one annotation per test, because the branch that decides an
# annotation is unnameable is the branch that puts `Any` in a published stub —
# a silent widening no type checker downstream can report, since the stub it
# reads is already the answer.


_T = TypeVar("_T")

# Annotation carriers: only their signatures are read, never their bodies, so
# each raises rather than returning. An `...` body would be a genuine type error
# in all but the first two — the return annotation promises a value the function
# never produces — and suppressing that in thirteen places would cost more than
# the one word it takes to be honest.


def _never() -> Any:
    raise NotImplementedError("declared for its annotation; never called")


def _returns_none() -> None: ...


def _returns_any() -> Any:
    return _never()


def _returns_union() -> int | str:
    return _never()


def _returns_optional() -> int | None:
    return _never()


def _returns_literal() -> Literal["read", "write"]:
    return _never()


def _returns_bare_list() -> list:
    return _never()


def _returns_parameterized() -> dict[str, list[int]]:
    return _never()


def _returns_callable_params() -> Callable[[int, str], bool]:
    return _never()


def _returns_callable_ellipsis() -> Callable[..., bool]:
    return _never()


def _returns_unresolvable() -> Nowhere:  # noqa: F821 # ty: ignore[unresolved-reference]
    # The unresolvable annotation *is* the fixture: both checkers are right that
    # `Nowhere` does not resolve, which is exactly what the renderer must meet.
    return _never()


def _returns_empty_tuple() -> tuple[()]:
    return _never()


def _returns_abstract_generic() -> Sequence[int]:
    return _never()


def _returns_type_variable() -> _T:
    return _never()


@pytest.mark.parametrize(
    ("func", "expected"),
    [
        (_returns_none, "None"),
        (_returns_any, "Any"),
        (_returns_union, "int | str"),
        (_returns_optional, "int | None"),
        (_returns_literal, "Literal['read', 'write']"),
        (_returns_bare_list, "list"),
        (_returns_parameterized, "dict[str, list[int]]"),
    ],
)
def test_an_annotation_renders_as_itself(func, expected):
    reference = reference_for(func)
    assert reference.expression.endswith(f"[[], {expected}]")
    assert not reference.degraded


def test_a_callable_annotation_keeps_its_parameter_list():
    reference = reference_for(_returns_callable_params)
    alias = alias_for("collections.abc", "Callable")
    assert reference.expression == f"{alias}[[], {alias}[[int, str], bool]]"
    assert not reference.degraded
    assert ("collections.abc", "Callable") in reference.imports


def test_a_callable_annotation_keeps_an_elided_parameter_list():
    reference = reference_for(_returns_callable_ellipsis)
    alias = alias_for("collections.abc", "Callable")
    assert reference.expression == f"{alias}[[], {alias}[..., bool]]"
    assert not reference.degraded


def test_an_unresolvable_annotation_degrades_instead_of_quoting_itself():
    reference = reference_for(_returns_unresolvable)
    assert reference.degraded
    assert "Nowhere" not in reference.expression
    assert reference.expression.endswith("[[], Any]")


def test_a_locally_defined_class_has_nothing_importable_to_name():
    class Local: ...

    reference = reference_for(Local)
    assert reference.degraded
    assert reference.expression == "Any"
    assert reference.imports == ()


def test_a_value_of_a_builtin_type_renders_without_an_import():
    reference = reference_for({"already": "a dict"})
    assert reference.expression == "dict"
    assert reference.imports == ()
    assert not reference.degraded


def test_none_renders_as_none_rather_than_its_type():
    reference = reference_for(None)
    assert reference.expression == "None"
    assert not reference.degraded


def test_a_callable_without_an_introspectable_signature_degrades():
    # `max` is a real builtin that `inspect.signature` refuses, which is the
    # condition this branch exists for — a mock would test the mock.
    reference = reference_for(max)
    alias = alias_for("collections.abc", "Callable")
    assert reference.expression == f"{alias}[..., Any]"
    assert reference.degraded


def test_an_empty_parameterization_renders_as_the_bare_origin():
    reference = reference_for(_returns_empty_tuple)
    assert reference.expression.endswith("[[], tuple]")
    assert not reference.degraded


@pytest.mark.parametrize(
    "func",
    [_returns_abstract_generic, _returns_type_variable],
    ids=["abstract-generic", "type-variable"],
)
def test_an_unnameable_annotation_degrades_rather_than_approximating(func):
    # A `Sequence[int]` is not `list[int]` and a type variable is not the type
    # it happens to bind to. Narrowing either to a concrete spelling would put a
    # claim in the stub that the source never made.
    reference = reference_for(func)
    assert reference.degraded
    assert reference.expression.endswith("[[], Any]")


def test_an_alias_is_derived_from_the_whole_module_path():
    # Two apps declaring `Product` is the collision the alias exists to make
    # impossible; the same input must also always give the same alias.
    assert alias_for("shop.models", "Product") != alias_for("blog.models", "Product")
    assert alias_for("shop.models", "Product") == alias_for("shop.models", "Product")
