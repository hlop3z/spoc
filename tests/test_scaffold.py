"""
Scaffolder tests: one per scenario in the `project-scaffolding` and
`scaffold-templates` specs, plus the structural guarantees from design.md
(pure core, one-way dependency, generated project starts unedited).
"""

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from spoc.core.exceptions import InvalidSegmentError
from spoc.scaffold import (
    DEFAULT_KINDS,
    DirectorySink,
    GenerationPlan,
    IncompleteTemplateSetError,
    InstalledTemplateSources,
    PathConflictError,
    PathEscapeError,
    PlannedFile,
    TargetNotEmptyError,
    TemplateSetNotFoundError,
    UndeclaredValueError,
    UnsatisfiedValueError,
    init_project,
)
from spoc.scaffold.core import (
    build_plan,
    declared_identifiers,
    detect_conflicts,
    validate_template_set,
)
from spoc.scaffold.plan import TemplateFile, TemplateSet
from spoc.scaffold.sources import load_from_directory


@pytest.fixture(autouse=True)
def clean_sys_path_and_modules():
    """Keep generated-project imports from leaking between tests."""
    path_before = list(sys.path)
    modules_before = set(sys.modules)
    yield
    sys.path[:] = path_before
    for name in set(sys.modules) - modules_before:
        del sys.modules[name]


def generate(destination: Path, **kwargs) -> GenerationPlan:
    """Generate with the real template set into `destination`."""
    return init_project(
        source=InstalledTemplateSources(),
        sink=DirectorySink(destination),
        project_name=kwargs.pop("project_name", "demo_project"),
        **kwargs,
    )


def fake_set(*files: TemplateFile, values: tuple[str, ...] = ()) -> TemplateSet:
    return TemplateSet(name="fake", values=values, files=files)


# ── Generating a runnable project ─────────────────────────────────────────


def test_generated_project_starts_unedited(tmp_path):
    """The scenario that keeps templates honest as the kernel evolves."""
    destination = tmp_path / "proj"
    generate(destination)

    # Imported from the project that was just generated, not from this repo.
    sys.path.insert(0, str(destination))
    from framework import framework

    framework.start(destination)
    try:
        identifiers = {c.identifier for c in framework.registry}
        assert identifiers == {"models:core.example", "views:core.example"}
        assert framework.installed_apps == ["core"]
    finally:
        framework.shutdown()


def test_generated_names_agree_across_files(tmp_path):
    destination = tmp_path / "proj"
    generate(destination, app_name="billing", kinds=("models", "views"))

    config = tomllib.loads((destination / "config" / "spoc.toml").read_text())
    listed = [app for apps in config["spoc"]["apps"].values() for app in apps]
    assert listed == ["billing"]
    assert (destination / "apps" / "billing").is_dir()

    declaration = (destination / "framework.py").read_text()
    for kind in ("models", "views"):
        assert f'"{kind}"' in declaration
        assert (destination / "apps" / "billing" / f"{kind}.py").is_file()


def test_generated_app_is_a_usable_example(tmp_path):
    """The cut of `add app` depends on this being an adequate copy source."""
    destination = tmp_path / "proj"
    generate(destination, kinds=("models", "views", "tasks"))

    for kind in ("models", "views", "tasks"):
        body = (destination / "apps" / "core" / f"{kind}.py").read_text()
        assert f"from framework import {kind}" in body
        assert f"@{kind}" in body
        assert "class Example" in body


def test_custom_kinds_are_declared_and_emitted(tmp_path):
    destination = tmp_path / "proj"
    generate(destination, kinds=("widgets",))

    declaration = (destination / "framework.py").read_text()
    assert 'spoc.Framework("widgets")' in declaration
    assert 'widgets = framework.kind("widgets")' in declaration
    assert (destination / "apps" / "core" / "widgets.py").is_file()
    assert not (destination / "apps" / "core" / "models.py").exists()


def test_target_directory_must_be_empty(tmp_path):
    destination = tmp_path / "proj"
    destination.mkdir()
    (destination / "already-here.txt").write_text("mine")

    with pytest.raises(TargetNotEmptyError):
        generate(destination)

    assert list(destination.iterdir()) == [destination / "already-here.txt"]


def test_absent_directory_is_acceptable(tmp_path):
    destination = tmp_path / "nested" / "proj"
    generate(destination)
    assert (destination / "main.py").is_file()


def test_at_least_one_kind_required(tmp_path):
    with pytest.raises(ValueError):
        generate(tmp_path / "proj", kinds=())


# ── Generation never destroys existing content ────────────────────────────


def test_conflicting_path_refused_and_existing_untouched(tmp_path):
    destination = tmp_path / "proj"
    (destination / "config").mkdir(parents=True)
    (destination / "config" / "spoc.toml").write_text("keep me")

    with pytest.raises(TargetNotEmptyError):
        generate(destination)

    assert (destination / "config" / "spoc.toml").read_text() == "keep me"


def test_detect_conflicts_names_the_colliding_path():
    plan = GenerationPlan(files=(PlannedFile(path="a/b.py", content=""),))
    with pytest.raises(PathConflictError) as exc:
        detect_conflicts(plan, ("a/b.py",))
    assert "a/b.py" in str(exc.value)


def test_failure_leaves_nothing_behind(tmp_path):
    """A sink that fails partway must not leave a half-written tree."""
    destination = tmp_path / "proj"
    sink = DirectorySink(destination)

    plan = GenerationPlan(
        files=(
            PlannedFile(path="ok.py", content="fine"),
            PlannedFile(path="bad/../../escape.py", content="nope"),
        )
    )
    with pytest.raises(PathEscapeError):
        sink.commit(plan)

    assert not destination.exists()
    assert not (tmp_path / "escape.py").exists()


def test_failure_in_an_existing_directory_leaves_it_empty(tmp_path, monkeypatch):
    """All-or-nothing must hold on the per-file fallback path, not just the swap."""
    import os

    destination = tmp_path / "proj"
    destination.mkdir()
    sink = DirectorySink(destination)
    plan = GenerationPlan(
        files=(
            PlannedFile(path="a.txt", content="a"),
            PlannedFile(path="pkg/deep/b.txt", content="b"),
            PlannedFile(path="c.txt", content="c"),
        )
    )

    real_rmdir = os.rmdir

    def deny_rmdir(path):
        # Only the destination itself is unremovable (it is "in use"); its
        # subdirectories behave normally, as they would for a real cwd.
        if Path(path) == destination:
            raise OSError("directory is in use")
        return real_rmdir(path)

    real_replace = os.replace
    calls = {"count": 0}

    def flaky_replace(src, dst):
        # Fail on the last move, after files and their directories exist.
        calls["count"] += 1
        if calls["count"] == 3:
            raise OSError("disk full")
        return real_replace(src, dst)

    monkeypatch.setattr("spoc.scaffold.sink.os.rmdir", deny_rmdir)
    monkeypatch.setattr("spoc.scaffold.sink.os.replace", flaky_replace)

    with pytest.raises(OSError, match="disk full"):
        sink.commit(plan)

    assert list(destination.iterdir()) == []


def test_failed_swap_puts_the_destination_back(tmp_path, monkeypatch):
    """The destination is removed only to make room — a failed move restores it."""
    import os

    destination = tmp_path / "proj"
    destination.mkdir()
    sink = DirectorySink(destination)
    plan = GenerationPlan(files=(PlannedFile(path="a.txt", content="a"),))

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("spoc.scaffold.sink.os.replace", failing_replace)

    with pytest.raises(OSError, match="disk full"):
        sink.commit(plan)

    assert destination.is_dir()
    assert list(destination.iterdir()) == []
    assert os.path.exists(destination)


def test_staging_directory_is_cleaned_up(tmp_path):
    destination = tmp_path / "proj"
    generate(destination)
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".spoc-scaffold-")]
    assert leftovers == []


# ── Names are validated before writing ────────────────────────────────────


@pytest.mark.parametrize("bad", ["PascalCase", "with-hyphen", "9leading", ""])
def test_invalid_project_name_rejected(tmp_path, bad):
    with pytest.raises((InvalidSegmentError, PathEscapeError)):
        generate(tmp_path / "proj", project_name=bad)
    assert not (tmp_path / "proj").exists()


def test_invalid_app_name_rejected(tmp_path):
    with pytest.raises(InvalidSegmentError):
        generate(tmp_path / "proj", app_name="Not Valid")
    assert not (tmp_path / "proj").exists()


@pytest.mark.parametrize("bad", ["../escape", "a/b", "a\\b", "c:evil"])
def test_traversal_in_name_rejected(tmp_path, bad):
    with pytest.raises(PathEscapeError):
        generate(tmp_path / "proj", app_name=bad)
    assert not (tmp_path / "proj").exists()


def test_cli_reports_an_invalid_name_instead_of_crashing(tmp_path, capsys, monkeypatch):
    """The kernel's identity errors exit like any other refusal — code 1, no traceback."""
    from spoc.scaffold.cli import main

    monkeypatch.chdir(tmp_path)
    assert main(["init", "BadName"]) == 1
    assert capsys.readouterr().err.startswith("error:")
    assert not (tmp_path / "BadName").exists()


def test_rendered_target_escaping_root_rejected():
    template = fake_set(
        TemplateFile(source="t", target="../$app_name.py", content="x"),
        values=("app_name",),
    )
    with pytest.raises(PathEscapeError):
        build_plan(template, {"app_name": "demo"}, ("models",))


# ── Dependency footprint ──────────────────────────────────────────────────


def test_kernel_does_not_import_the_scaffolder():
    """The dependency runs one way, so the scaffolder is removable."""
    code = (
        "import sys, spoc; "
        "spoc.Framework('models'); "
        "print([m for m in sys.modules if 'scaffold' in m])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


def test_core_imports_nothing_beyond_stdlib_and_kernel():
    """design.md D1: the core stays pure."""
    source = (Path(__file__).parent.parent / "src/spoc/scaffold/core.py").read_text()
    for line in source.splitlines():
        if line.startswith(("import ", "from ")):
            assert "spoc.scaffold" not in line or line.startswith("from ."), line
    # The only non-stdlib import is the kernel's own grammar.
    assert "from ..core.identity import validate_segment" in source


def test_published_dependencies_stay_empty():
    """The invariant the whole build-vs-adopt gate was run to protect."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == []


def test_the_scaffolder_needs_no_optional_dependency():
    """Extras exist for the data surface; every scaffolder decision landed on stdlib,
    so nothing under `spoc/scaffold/` may import anything outside it."""
    import ast
    import sys

    for path in sorted(
        (Path(__file__).parent.parent / "src/spoc/scaffold").rglob("*.py")
    ):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] in sys.stdlib_module_names, (
                        alias.name
                    )
            elif isinstance(node, ast.ImportFrom) and not node.level:
                assert (node.module or "").split(".")[0] in sys.stdlib_module_names, (
                    node.module
                )


# ── Template sets: shape is data ──────────────────────────────────────────


def test_shape_changes_without_touching_code(tmp_path):
    """Adding a file to the declared shape changes the output, not the program."""
    root = tmp_path / "set"
    (root / "files").mkdir(parents=True)
    (root / "files" / "extra.txt.tmpl").write_text("for $project_name")
    (root / "manifest.toml").write_text(
        '[template_set]\nname = "tiny"\nvalues = ["project_name"]\n\n'
        '[[files]]\nsource = "files/extra.txt.tmpl"\ntarget = "EXTRA.txt"\n'
    )

    loaded = load_from_directory(root)
    plan = build_plan(loaded, {"project_name": "demo"}, ("models",))
    assert plan.paths == ("EXTRA.txt",)
    assert plan.files[0].content == "for demo"


def test_builtin_template_files_carry_their_native_format():
    """Each template is stored in the format it is emitted as."""
    root = Path(__file__).parent.parent / "src/spoc/scaffold/templates/default"
    assert (root / "manifest.toml").is_file()
    sources = [f.source for f in load_from_directory(root).files]
    assert all(s.endswith(".tmpl") for s in sources)
    for source in sources:
        stem = source[: -len(".tmpl")]
        assert stem.endswith((".py", ".toml")), stem


def test_default_template_set_used_when_none_named(tmp_path):
    destination = tmp_path / "proj"
    generate(destination)
    assert (destination / "config" / "spoc.toml").is_file()


def test_downstream_template_set_is_used(tmp_path):
    """A framework built on the kernel supplies its own shape."""
    root = tmp_path / "downstream"
    root.mkdir()
    (root / "only.py.tmpl").write_text("# $project_name, downstream style\n")
    (root / "manifest.toml").write_text(
        '[template_set]\nname = "downstream"\nvalues = ["project_name"]\n\n'
        '[[files]]\nsource = "only.py.tmpl"\ntarget = "only.py"\n'
    )

    class OneSetSource:
        def available(self):
            return ("downstream",)

        def load(self, name):
            if name != "downstream":
                raise TemplateSetNotFoundError(name, self.available())
            return load_from_directory(root)

    destination = tmp_path / "proj"
    init_project(
        source=OneSetSource(),
        sink=DirectorySink(destination),
        project_name="demo",
        template_set="downstream",
    )
    assert (destination / "only.py").read_text() == "# demo, downstream style\n"
    assert not (destination / "config").exists()


def test_unknown_template_set_lists_candidates(tmp_path):
    with pytest.raises(TemplateSetNotFoundError) as exc:
        generate(tmp_path / "proj", template_set="nope")
    assert "default" in str(exc.value)
    assert not (tmp_path / "proj").exists()


# ── Template sets: validated before use ───────────────────────────────────


def test_incomplete_template_set_names_what_is_missing(tmp_path):
    root = tmp_path / "set"
    root.mkdir()
    (root / "manifest.toml").write_text(
        '[template_set]\nname = "broken"\nvalues = []\n\n'
        '[[files]]\nsource = "absent.py.tmpl"\ntarget = "absent.py"\n'
    )
    with pytest.raises(IncompleteTemplateSetError) as exc:
        load_from_directory(root)
    assert "absent.py.tmpl" in str(exc.value)


def test_manifest_without_files_is_incomplete(tmp_path):
    root = tmp_path / "set"
    root.mkdir()
    (root / "manifest.toml").write_text('[template_set]\nname = "empty"\nvalues = []\n')
    with pytest.raises(IncompleteTemplateSetError):
        load_from_directory(root)


def test_unsatisfiable_substitution_named(tmp_path):
    template = fake_set(
        TemplateFile(source="t", target="out.py", content="$needed"),
        values=("needed",),
    )
    with pytest.raises(UnsatisfiedValueError) as exc:
        validate_template_set(template, {})
    assert "needed" in str(exc.value)


def test_undeclared_placeholder_rejected():
    """The manifest's declaration must be honest, not merely present."""
    template = fake_set(
        TemplateFile(source="sneaky.tmpl", target="out.py", content="$undeclared"),
        values=(),
    )
    with pytest.raises(UndeclaredValueError) as exc:
        validate_template_set(template, {"undeclared": "x"})
    assert "sneaky.tmpl" in str(exc.value)


def test_kind_placeholder_needs_a_per_kind_file():
    """The repetition supplies ``kind`` only to per_kind files — a plain file
    using it must be refused at validation, not crash mid-render."""
    template = fake_set(
        TemplateFile(source="t.tmpl", target="out.txt", content="hello $kind"),
        values=("kind",),
    )
    with pytest.raises(UnsatisfiedValueError) as exc:
        build_plan(template, {}, ("models",))
    assert "kind" in str(exc.value)


# ── Template sets: substitution values are declared ───────────────────────


def test_declared_values_are_enumerable_without_rendering():
    root = Path(__file__).parent.parent / "src/spoc/scaffold/templates/default"
    loaded = load_from_directory(root)
    used = set(declared_identifiers(loaded))
    assert used
    assert used <= set(loaded.values)


def test_template_content_is_not_executed(tmp_path):
    """Executable-looking content is emitted verbatim, never run."""
    root = tmp_path / "set"
    root.mkdir()
    marker = tmp_path / "should-not-exist.txt"
    (root / "danger.py.tmpl").write_text(
        f"import pathlib\npathlib.Path({str(marker)!r}).write_text('ran')\n"
    )
    (root / "manifest.toml").write_text(
        '[template_set]\nname = "danger"\nvalues = []\n\n'
        '[[files]]\nsource = "danger.py.tmpl"\ntarget = "danger.py"\n'
    )

    destination = tmp_path / "proj"
    init_project(
        source=type(
            "S",
            (),
            {
                "available": lambda self: ("danger",),
                "load": lambda self, name: load_from_directory(root),
            },
        )(),
        sink=DirectorySink(destination),
        project_name="demo",
        template_set="danger",
    )

    assert not marker.exists()
    assert "write_text" in (destination / "danger.py").read_text()


def test_plan_is_immutable():
    plan = GenerationPlan(files=(PlannedFile(path="a.py", content="x"),))
    with pytest.raises(AttributeError):
        plan.files = ()  # ty: ignore[invalid-assignment]


def test_default_kinds_are_the_documented_pair():
    assert DEFAULT_KINDS == ("models", "views")
