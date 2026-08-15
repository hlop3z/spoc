"""
Scaffold parity (specs: scaffold-templates, project-scaffolding): directory
template-set references, and `spoc app` — one test per delta scenario.
"""

import shutil
import sys
from pathlib import Path

import pytest

from spoc.cli import main as cli_main
from spoc.scaffold.errors import IncompleteTemplateSetError, TargetNotEmptyError
from spoc.scaffold.operations import AddedApp, add_app, init_project
from spoc.scaffold.sink import DirectorySink
from spoc.scaffold.sources import InstalledTemplateSources
from spoc.testing import import_state

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")

BUILTIN_TEMPLATES = Path(__file__).parent.parent / "src/spoc/scaffold/templates/default"


def _generate(destination: Path, **kwargs) -> None:
    init_project(
        source=InstalledTemplateSources(),
        sink=DirectorySink(destination),
        project_name="parityproj",
        **kwargs,
    )


# ── Directory template-set references ─────────────────────────────────────


def test_directory_path_is_a_valid_template_set_reference(tmp_path):
    """Spec: a path resolves identically to an installed set."""
    local_set = tmp_path / "myset"
    shutil.copytree(BUILTIN_TEMPLATES, local_set)

    by_path = tmp_path / "by_path"
    by_name = tmp_path / "by_name"
    _generate(by_path, template_set=str(local_set))
    _generate(by_name)

    relative = sorted(p.relative_to(by_path) for p in by_path.rglob("*") if p.is_file())
    assert relative == sorted(
        p.relative_to(by_name) for p in by_name.rglob("*") if p.is_file()
    )


def test_directory_without_manifest_fails_naming_it_writing_nothing(tmp_path):
    empty_set = tmp_path / "notaset"
    empty_set.mkdir()
    destination = tmp_path / "out"
    with pytest.raises(IncompleteTemplateSetError, match=r"manifest\.toml"):
        _generate(destination, template_set=str(empty_set))
    assert not destination.exists()


def test_bare_name_never_resolves_to_a_local_directory(tmp_path, monkeypatch):
    """The separator is the discriminator: a directory named like a set name
    does not shadow the installed set."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "default").mkdir()  # would be a broken set if resolved
    destination = tmp_path / "out"
    _generate(destination)  # resolves the builtin, not ./default
    assert (destination / "framework.py").exists()


# ── add_app ───────────────────────────────────────────────────────────────


def _project(tmp_path: Path) -> Path:
    base = tmp_path / "proj"
    _generate(base, kinds=("models", "views"))
    return base


def _add(base: Path, name: str, kinds=("models", "views")) -> AddedApp:
    return add_app(
        source=InstalledTemplateSources(),
        sink_factory=lambda app_dir: DirectorySink(base / app_dir),
        app_name=name,
        kinds=kinds,
    )


def test_added_app_matches_the_generated_shape(tmp_path):
    base = _project(tmp_path)
    added = _add(base, "blog")

    generated = sorted(
        p.name for p in (base / "apps" / "core").iterdir() if p.is_file()
    )
    new = sorted(p.name for p in (base / "apps" / "blog").iterdir() if p.is_file())
    assert new == generated  # __init__ plus one module per kind
    assert added.app_dir == "apps/blog"
    assert added.config_reference == "apps.blog"


def test_added_app_registers_on_next_boot_once_configured(tmp_path):
    """Spec: the new app registers successfully once installed."""
    base = _project(tmp_path)
    _add(base, "blog")
    config = base / "config" / "spoc.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'production = ["apps.core"]',
            'production = ["apps.core", "apps.blog"]',
        ),
        encoding="utf-8",
    )

    with import_state():
        sys.path.insert(0, str(base))
        import spoc

        fw = spoc.Framework("models", "views").start(base)
        assert "models:blog.example" in {c.identifier for c in fw.registry}
        fw.shutdown()


def test_existing_app_is_never_overwritten(tmp_path):
    base = _project(tmp_path)
    marker = base / "apps" / "core" / "models.py"
    before = marker.read_bytes()
    with pytest.raises(TargetNotEmptyError, match="core"):
        _add(base, "core")
    assert marker.read_bytes() == before


def test_configuration_is_stated_not_edited(tmp_path, capsys):
    base = _project(tmp_path)
    config_before = (base / "config" / "spoc.toml").read_bytes()

    code = cli_main(["app", "blog", "--path", str(base), "--kinds", "models,views"])
    assert code == 0
    assert (base / "config" / "spoc.toml").read_bytes() == config_before
    out = capsys.readouterr().out
    assert '"apps.blog"' in out and "[spoc.apps]" in out


def test_kinds_derive_from_the_declaration(tmp_path, capsys):
    base = _project(tmp_path)  # declares models + views
    assert cli_main(["app", "shop", "--path", str(base)]) == 0
    modules = sorted(p.name for p in (base / "apps" / "shop").iterdir() if p.is_file())
    assert modules == ["__init__.py", "models.py", "views.py"]


def test_no_kinds_and_no_declaration_is_actionable(tmp_path, capsys):
    bare = tmp_path / "bare"
    bare.mkdir()
    assert cli_main(["app", "blog", "--path", str(bare)]) == 1
    err = capsys.readouterr().err
    assert "--kinds" in err and "framework" in err


def test_add_app_requires_at_least_one_kind(tmp_path):
    base = _project(tmp_path)
    with pytest.raises(ValueError, match="at least one kind"):
        _add(base, "blog", kinds=())


def test_app_files_without_a_common_directory_are_refused(tmp_path):
    """A set whose app files land at the project root has no app directory to
    scope the commit to — refused, nothing written."""
    local_set = tmp_path / "flat"
    local_set.mkdir()
    (local_set / "manifest.toml").write_text(
        '[template_set]\nname = "flat"\ndescription = "flat"\n'
        'values = ["app_name"]\n\n'
        '[[files]]\nsource = "app.py.tmpl"\ntarget = "$app_name.py"\n',
        encoding="utf-8",
    )
    (local_set / "app.py.tmpl").write_text("# $app_name\n", encoding="utf-8")

    base = _project(tmp_path)
    with pytest.raises(IncompleteTemplateSetError, match="common app directory"):
        add_app(
            source=InstalledTemplateSources(),
            sink_factory=lambda app_dir: DirectorySink(base / app_dir),
            app_name="blog",
            kinds=("models",),
            template_set=str(local_set),
        )


def test_app_without_kinds_and_without_derivation_is_actionable(capsys):
    """The scaffold's own surface degrades actionably when no composition
    root injected derivation (spoc.cli always does): the refusal renders as
    the mount's one-line error, not as an exception the mounting parser's
    author has to know to catch."""
    import argparse

    from spoc.scaffold import cli as scaffold_cli

    parser = argparse.ArgumentParser()
    scaffold_cli.register(parser.add_subparsers())  # no derive_kinds
    args = parser.parse_args(["app", "blog"])

    assert args.handler(args) == 1
    err = capsys.readouterr().err
    assert err.startswith("error:") and "--kinds" in err


def test_template_set_without_app_files_is_refused(tmp_path):
    """A set that has no $app_name-marked targets cannot add apps."""
    local_set = tmp_path / "noapp"
    shutil.copytree(BUILTIN_TEMPLATES, local_set)
    manifest = local_set / "manifest.toml"
    text = manifest.read_text(encoding="utf-8")
    for block in list(text.split("[[files]]")):
        if "$app_name" in block:
            text = text.replace("[[files]]" + block, "")
    manifest.write_text(text, encoding="utf-8")

    base = _project(tmp_path)
    with pytest.raises(IncompleteTemplateSetError, match="app templates"):
        add_app(
            source=InstalledTemplateSources(),
            sink_factory=lambda app_dir: DirectorySink(base / app_dir),
            app_name="blog",
            kinds=("models",),
            template_set=str(local_set),
        )
