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

from spoc.cli import main as cli_main
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
    ReservedTargetError,
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
from spoc.scaffold.provenance import RECORD_NAME
from spoc.scaffold.sources import BUILTIN_SET, load_from_directory


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


class _OneSet:
    """A source holding exactly one set — what a downstream framework mounts."""

    def __init__(self, loaded: TemplateSet) -> None:
        self._loaded = loaded

    def available(self) -> tuple[str, ...]:
        return (self._loaded.name,)

    def load(self, name: str) -> TemplateSet:
        if name != self._loaded.name:
            raise TemplateSetNotFoundError(name, self.available())
        return self._loaded


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
        assert framework.installed_apps == ["apps.core"]
    finally:
        framework.shutdown()


def test_generated_names_agree_across_files(tmp_path):
    destination = tmp_path / "proj"
    generate(destination, app_name="billing", kinds=("models", "views"))

    config = tomllib.loads((destination / "config" / "spoc.toml").read_text())
    listed = [app for apps in config["spoc"]["apps"].values() for app in apps]
    assert listed == ["apps.billing"]
    assert (destination / "apps" / "__init__.py").is_file()
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

    def deny_rmdir(path, *, dir_fd=None):
        # Only the destination itself is unremovable (it is "in use"); its
        # subdirectories behave normally, as they would for a real cwd.
        #
        # The signature mirrors os.rmdir's on purpose: patching the attribute
        # on `spoc.scaffold.sink.os` patches the os module itself, so the
        # sink's own cleanup rmtree calls this too — and on POSIX it removes
        # directories relative to an open fd. A stub taking only a path fails
        # there while passing on Windows, where rmtree never passes dir_fd.
        if dir_fd is None and Path(path) == destination:
            raise OSError("directory is in use")
        return real_rmdir(path, dir_fd=dir_fd)

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


def test_commit_refuses_a_non_empty_destination(tmp_path):
    """Never-overwrite is the sink's own guarantee, not just its callers'."""
    destination = tmp_path / "occupied"
    destination.mkdir()
    (destination / "keep.txt").write_text("precious", encoding="utf-8")
    sink = DirectorySink(destination)
    plan = GenerationPlan(files=(PlannedFile(path="a.txt", content="a"),))

    with pytest.raises(TargetNotEmptyError):
        sink.commit(plan)

    assert (destination / "keep.txt").read_text(encoding="utf-8") == "precious"
    assert not (destination / "a.txt").exists()


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
    from spoc.cli import main

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

    destination = tmp_path / "proj"
    init_project(
        source=_OneSet(load_from_directory(root)),
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


def test_reserved_destination_is_refused():
    """A set may not claim the destination the operation writes itself."""
    template = fake_set(
        TemplateFile(source="forge.tmpl", target=RECORD_NAME, content="forged"),
        values=(),
    )
    with pytest.raises(ReservedTargetError) as exc:
        build_plan(template, {}, ("models",))
    assert RECORD_NAME in str(exc.value)


def test_reserved_destination_is_refused_however_it_is_spelled():
    """Checked on the rendered path, so substitution is not a way around it."""
    template = fake_set(
        TemplateFile(source="forge.tmpl", target="$sneaky", content="forged"),
        values=("sneaky",),
    )
    with pytest.raises(ReservedTargetError):
        build_plan(template, {"sneaky": RECORD_NAME}, ("models",))


def test_reserved_destination_is_refused_end_to_end(tmp_path):
    """And nothing is written when it is — a forgery attempt is not partial."""
    root = tmp_path / "set"
    root.mkdir()
    (root / "forge.tmpl").write_text("forged\n")
    (root / "manifest.toml").write_text(
        '[template_set]\nname = "forger"\nvalues = []\n\n'
        f'[[files]]\nsource = "forge.tmpl"\ntarget = "{RECORD_NAME}"\n'
    )
    destination = tmp_path / "proj"
    with pytest.raises(ReservedTargetError):
        init_project(
            source=_OneSet(load_from_directory(root)),
            sink=DirectorySink(destination),
            project_name="demo",
            template_set="forger",
        )
    assert not destination.exists()


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


# ── The CLI adapter: argv in, exit code out ───────────────────────────────


class TestCommandLine:
    """The argv layer itself.

    `init_project` is covered thoroughly elsewhere; what these pin is the glue —
    that each flag reaches the operation it names, and that a refusal becomes an
    exit code rather than a traceback.
    """

    def test_init_generates_a_project(self, tmp_path, capsys):
        target = tmp_path / "generated"

        code = cli_main(["init", "myproject", "--path", str(target)])

        assert code == 0
        assert (target / "main.py").is_file()
        assert (target / "config" / "spoc.toml").is_file()
        out = capsys.readouterr().out
        assert str(target) in out
        assert "python main.py" in out

    def test_path_defaults_to_the_project_name_under_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        assert cli_main(["init", "defaulted"]) == 0

        assert (tmp_path / "defaulted" / "main.py").is_file()

    def test_app_and_kinds_flags_reach_the_generated_project(self, tmp_path):
        target = tmp_path / "flagged"

        code = cli_main(
            [
                "init",
                "flagproj",
                "--path",
                str(target),
                "--app",
                "shop",
                "--kinds",
                "models,views",
            ]
        )

        assert code == 0
        assert (target / "apps" / "shop" / "models.py").is_file()
        assert (target / "apps" / "shop" / "views.py").is_file()
        assert "shop" in (target / "config" / "spoc.toml").read_text()

    def test_kinds_flag_tolerates_whitespace_and_empty_entries(self, tmp_path):
        target = tmp_path / "spaced"

        assert (
            cli_main(
                [
                    "init",
                    "spacedproj",
                    "--path",
                    str(target),
                    "--kinds",
                    " models , ,views ",
                ]
            )
            == 0
        )

        assert (target / "apps" / "core" / "models.py").is_file()
        assert (target / "apps" / "core" / "views.py").is_file()

    def test_unknown_template_set_is_an_exit_code_not_a_traceback(
        self, tmp_path, capsys
    ):
        code = cli_main(
            ["init", "tmplproj", "--path", str(tmp_path / "out"), "--template", "nope"]
        )

        assert code == 1
        assert "error:" in capsys.readouterr().err

    def test_invalid_project_name_exits_one(self, tmp_path, capsys):
        code = cli_main(["init", "Not-Valid", "--path", str(tmp_path / "out")])

        assert code == 1
        assert "error:" in capsys.readouterr().err

    def test_a_non_empty_target_is_refused_without_writing(self, tmp_path, capsys):
        target = tmp_path / "occupied"
        target.mkdir()
        (target / "main.py").write_text("# mine\n")

        code = cli_main(["init", "occupiedproj", "--path", str(target)])

        assert code == 1
        assert "error:" in capsys.readouterr().err
        assert (target / "main.py").read_text() == "# mine\n", (
            "existing content changed"
        )

    def test_a_missing_subcommand_is_a_usage_error(self):
        with pytest.raises(SystemExit) as exc:
            cli_main([])
        assert exc.value.code == 2


# ── Path escapes: every form the platform would resolve outward ───────────


class TestPathEscapeForms:
    """A template set is third-party content, so this is a trust boundary.

    Each of these is refused in the pure layer, before any filesystem call —
    the sink's own resolve check stays as defense in depth, not as the only
    line of defense.
    """

    @pytest.mark.parametrize(
        "target",
        [
            "../escaped.py",
            "..\\escaped.py",
            "apps/../../escaped.py",
            "apps\\..\\..\\escaped.py",
            "/etc/passwd",
            "\\\\server\\share\\x.py",
            "C:/Windows/System32/evil.py",
            "C:\\Windows\\System32\\evil.py",
        ],
    )
    def test_escaping_targets_are_refused(self, target):
        template_set = TemplateSet(
            name="hostile",
            values=(),
            files=(TemplateFile(source="x.tmpl", target=target, content="x"),),
        )
        with pytest.raises(PathEscapeError):
            build_plan(template_set, {}, kinds=())

    @pytest.mark.parametrize(
        "target", ["main.py", "apps/core/models.py", "config/spoc.toml"]
    )
    def test_ordinary_targets_are_accepted(self, target):
        template_set = TemplateSet(
            name="fine",
            values=(),
            files=(TemplateFile(source="x.tmpl", target=target, content="x"),),
        )
        assert build_plan(template_set, {}, kinds=()).paths == (target,)


# ── Template sets from importable packages ────────────────────────────────


def test_an_importable_package_is_a_valid_template_set(tmp_path, monkeypatch):
    """The entry-point group's documented contract, honored.

    `str(module)` is a repr, not a path — resolving a package target that way
    produced a misleading "template set not found".
    """
    package_root = tmp_path / "vendor_templates"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("")
    (package_root / "manifest.toml").write_text(
        '[template_set]\nname = "vendor"\nvalues = ["project_name"]\n\n'
        '[[files]]\nsource = "main.py.tmpl"\ntarget = "main.py"\n'
    )
    (package_root / "main.py.tmpl").write_text("# ${project_name}\n")

    monkeypatch.syspath_prepend(str(tmp_path))
    import vendor_templates

    class PackageEntry:
        name = "vendor"

        def load(self):
            return vendor_templates

    monkeypatch.setattr(
        "spoc.scaffold.sources._entry_points", lambda: {"vendor": PackageEntry()}
    )

    loaded = InstalledTemplateSources().load("vendor")

    assert loaded.name == "vendor"
    assert [f.target for f in loaded.files] == ["main.py"]


def test_the_builtin_set_resolves_through_importlib_resources():
    """Works however the distribution is installed, including non-directory."""
    loaded = InstalledTemplateSources().load(BUILTIN_SET)
    assert loaded.name
    assert loaded.files
