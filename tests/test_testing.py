"""
Test-harness suite: containment boundary, isolation scope, tree builder,
mode override, and the pytest plugin — one test per spec scenario, plus the
boundary contracts the other contained subpackages also pin.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import spoc
from spoc.testing import ProjectTree, isolated, mode

pytest_plugins = ["pytester"]

MODELS_BODY = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Post:
        ...
"""


# ── Containment boundary ──────────────────────────────────────────────────


def test_no_kernel_module_imports_the_test_harness():
    """Same contract as formats/scaffold: the boundary holds in source.

    `spoc.diagnostics` is the one allowed importer — a diagnostic run is an
    isolated dry boot, and it composes the harness's scopes rather than
    duplicating them (design ADR). It is a surface, not kernel.
    """
    root = Path(__file__).parent.parent / "src/spoc"
    for path in sorted(root.rglob("*.py")):
        if (root / "testing") in path.parents or (root / "diagnostics") in path.parents:
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
                assert "testing" not in name.split("."), f"{path.name}: {name}"


def test_importing_spoc_never_loads_the_harness():
    """Kernel never loads the harness — pinned in a fresh interpreter."""
    code = (
        "import sys; import spoc; "
        "print([m for m in sys.modules if m.startswith('spoc.testing')])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


def test_importing_the_harness_never_loads_pytest():
    """The plugin module is pytest's to import, not ours: a plain script using
    the harness stays runner-free."""
    code = (
        "import sys; import spoc.testing; "
        "print([m for m in sys.modules "
        "if m == 'pytest' or m == 'spoc.testing.plugin'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


# ── Isolation scope ───────────────────────────────────────────────────────


def _tree(tmp_path: Path, name: str = "project") -> Path:
    return ProjectTree(apps={"blog": {"models": MODELS_BODY}}).build(tmp_path, name)


def test_isolated_restores_state_after_normal_exit(tmp_path):
    base = _tree(tmp_path)
    path_before = list(sys.path)
    modules_before = set(sys.modules)

    with isolated(base, "models") as fw:
        assert fw.started
        assert fw.resolve("models:blog.post").object.__name__ == "Post"

    assert not fw.started
    assert sys.path == path_before
    assert set(sys.modules) == modules_before


def test_isolated_restores_state_after_an_exception(tmp_path):
    base = _tree(tmp_path)
    path_before = list(sys.path)
    modules_before = set(sys.modules)

    class Boom(Exception): ...

    fw_seen = None
    with pytest.raises(Boom), isolated(base, "models") as fw:
        fw_seen = fw
        raise Boom
    assert fw_seen is not None and not fw_seen.started
    assert sys.path == path_before
    assert set(sys.modules) == modules_before


def test_consecutive_scopes_are_independent(tmp_path):
    base_a = _tree(tmp_path, "alpha")
    base_b = ProjectTree(
        apps={"shop": {"models": MODELS_BODY.replace("Post", "Order")}}
    ).build(tmp_path, "beta")

    with isolated(base_a, "models") as fw:
        fw.resolve("models:blog.post")
    with isolated(base_b, "models") as fw:
        fw.resolve("models:shop.order")
        with pytest.raises(spoc.UnknownNamespaceError):
            fw.resolve("models:blog.post")


def test_isolated_refuses_kinds_and_framework_together(tmp_path):
    scope = isolated(_tree(tmp_path), "models", framework=spoc.Framework("models"))
    with pytest.raises(ValueError), scope:
        pass  # pragma: no cover


def test_isolated_with_prebuilt_framework_and_deferred_start(tmp_path):
    base = _tree(tmp_path)
    fw = spoc.Framework("models")
    seen = []
    fw.on_ready(lambda registry: seen.append(len(list(registry))))

    with isolated(base, framework=fw, start=False) as inert:
        assert not inert.started
        inert.start(base)
        assert seen == [1]
    assert not fw.started


def test_harness_works_in_a_plain_script(tmp_path):
    """Spec: no test runner present — the harness is importable and functional."""
    script = tmp_path / "plain.py"
    script.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "from spoc.testing import ProjectTree, isolated\n"
        "body = '''\n"
        "from spoc.core.declaration import component\n"
        "@component(kind='models')\n"
        "class Post: ...\n"
        "'''\n"
        "base = ProjectTree(apps={'blog': {'models': body}}).build(Path(sys.argv[1]))\n"
        "with isolated(base, 'models') as fw:\n"
        "    print(fw.resolve('models:blog.post').identifier)\n"
        "assert 'pytest' not in sys.modules\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path / "work")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "models:blog.post"


# ── Tree builder ──────────────────────────────────────────────────────────


def test_built_tree_boots_and_resolves(tmp_path):
    base = _tree(tmp_path)
    with isolated(base, "models") as fw:
        record = fw.resolve("models:blog.post")
        assert record.identifier == "models:blog.post"


def test_multiple_apps_and_config_entries(tmp_path):
    base = ProjectTree(
        apps={
            "blog": {"models": MODELS_BODY},
            "shop": {"models": MODELS_BODY.replace("Post", "Order")},
        },
        config={"mode": "staging", "apps": {"staging": ["blog", "shop"]}},
    ).build(tmp_path)

    with isolated(base, "models") as fw:
        assert fw.config is not None
        assert fw.config.project["mode"] == "staging"
        assert sorted(fw.installed_apps) == ["blog", "shop"]
        fw.resolve("models:blog.post")
        fw.resolve("models:shop.order")


# ── Mode override ─────────────────────────────────────────────────────────


def test_mode_override_applies_and_reverts(tmp_path):
    base = ProjectTree(
        apps={"blog": {"models": MODELS_BODY}},
        config={
            "mode": "development",
            "apps": {"development": ["blog"], "staging": []},
        },
    ).build(tmp_path)
    original = (base / "config" / "spoc.toml").read_bytes()

    with mode(base, "staging"), isolated(base, "models") as fw:
        assert fw.config is not None
        assert fw.config.project["mode"] == "staging"
        assert fw.installed_apps == []

    assert (base / "config" / "spoc.toml").read_bytes() == original
    with isolated(base, "models") as fw:
        assert fw.config is not None
        assert fw.config.project["mode"] == "development"
        assert fw.installed_apps == ["blog"]


def test_toml_emission_without_extra_names_it(tmp_path, monkeypatch):
    """The formats contract holds here too: a missing extra is named, never a
    transitive ImportError."""
    from spoc.testing import MissingDependencyError
    from spoc.testing.core import dump_toml

    monkeypatch.setitem(sys.modules, "tomli_w", None)
    with pytest.raises(MissingDependencyError, match=r"spoc\[toml\]"):
        dump_toml({"spoc": {"mode": "development"}})


def test_mode_override_without_config_file_refuses(tmp_path):
    with pytest.raises(FileNotFoundError), mode(tmp_path, "staging"):
        pass  # pragma: no cover


# ── Pytest plugin ─────────────────────────────────────────────────────────

PLUGIN_TEST = '''
MODELS = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Post:
        ...
"""

def test_fixtures_resolve_without_registration(spoc_framework):
    fw = spoc_framework("models", apps={"blog": {"models": MODELS}})
    assert fw.resolve("models:blog.post").identifier == "models:blog.post"
'''


def test_fixtures_available_without_registration(pytester):
    """Spec: install spoc + pytest, fixtures resolve by name — no conftest."""
    pytester.makepyfile(PLUGIN_TEST)
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=1)


def test_teardown_runs_when_a_test_fails(pytester):
    """Spec: a failing test still tears down; the next test sees clean state."""
    pytester.makepyfile(
        PLUGIN_TEST.replace(
            "def test_fixtures_resolve_without_registration",
            "def test_that_fails_after_boot",
        ).replace(
            'assert fw.resolve("models:blog.post").identifier == "models:blog.post"',
            "assert False",
        )
        + (
            "\n\nimport sys\n\n"
            "def test_no_leak_from_the_failed_test():\n"
            "    assert not [m for m in sys.modules if m.startswith('blog')]\n"
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=1, failed=1)
