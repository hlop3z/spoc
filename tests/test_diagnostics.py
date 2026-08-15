"""
Diagnostics suite: check/list/explain operations, framework location, the
composed CLI adapters, and the containment boundary — one test per spec
scenario in project-diagnostics.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from spoc.cli import main as cli_main
from spoc.diagnostics import LocateError, check, explain, list_records
from spoc.testing import ProjectTree

MODELS_BODY = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Post:
        ...
"""

SYNC_FRAMEWORK = 'import spoc\nframework = spoc.Framework("models")\n'

ASYNC_FRAMEWORK = (
    "import spoc\n"
    "async def up(objects): ...\n"
    'framework = spoc.Framework(spoc.KindSpec("models", on_startup=up))\n'
)


def project(
    tmp_path: Path,
    name: str = "proj",
    framework_body: str | None = SYNC_FRAMEWORK,
    apps: dict | None = None,
    config: dict | None = None,
) -> Path:
    """A bootable project with the scaffold's framework.py convention."""
    base = ProjectTree(
        apps=apps if apps is not None else {"blog": {"models": MODELS_BODY}},
        config=config or {},
    ).build(tmp_path, name)
    if framework_body is not None:
        (base / "framework.py").write_text(framework_body, encoding="utf-8")
    return base


# ── check ─────────────────────────────────────────────────────────────────


def test_clean_project_passes_and_leaves_no_residue(tmp_path):
    base = project(tmp_path)
    path_before = list(sys.path)
    modules_before = set(sys.modules)

    report = check(base)

    assert report.ok and report.findings == ()
    assert sys.path == path_before
    assert set(sys.modules) == modules_before


def test_unresolvable_app_reported_before_runtime(tmp_path):
    base = project(tmp_path, config={"apps": {"development": ["blog", "ghost_app"]}})
    report = check(base)
    assert not report.ok
    assert any("ghost_app" in f.message for f in report.findings)


def test_config_typing_problem_names_the_key(tmp_path):
    base = project(tmp_path, config={"apps": {"development": "notalist"}})
    report = check(base)
    assert not report.ok
    assert any(
        "spoc.apps.development" in f.message and f.area == "config"
        for f in report.findings
    )


def test_mode_absent_from_cascade_reported_with_kernel_text(tmp_path):
    base = project(tmp_path, config={"mode": "prod"})
    report = check(base)
    assert not report.ok
    assert any("prod" in f.message for f in report.findings)


def test_coroutine_hook_flagged_and_declaration_still_validated(tmp_path):
    base = project(tmp_path, framework_body=ASYNC_FRAMEWORK)
    report = check(base)
    # The refusal is the only problem: the async path validated the rest.
    assert [f.area for f in report.findings] == ["lifecycle"]
    assert "astart()" in report.findings[0].message


def test_check_exit_codes(tmp_path, capsys):
    clean = project(tmp_path, "cleanproj")
    assert cli_main(["check", str(clean)]) == 0
    assert "OK" in capsys.readouterr().out

    broken = project(tmp_path, "brokenproj", config={"apps": {"development": ["nope"]}})
    assert cli_main(["check", str(broken)]) == 1
    err = capsys.readouterr().err
    assert "nope" in err and "problem" in err


def test_library_and_cli_report_the_same_findings(tmp_path, capsys):
    base = project(tmp_path, config={"apps": {"development": ["blog", "gone"]}})
    report = check(base)
    cli_main(["check", str(base)])
    err = capsys.readouterr().err
    for finding in report.findings:
        assert finding.message in err


# ── list ──────────────────────────────────────────────────────────────────


def _two_app_project(tmp_path):
    return project(
        tmp_path,
        apps={
            "blog": {"models": MODELS_BODY},
            "shop": {"models": MODELS_BODY.replace("Post", "Order")},
        },
    )


def test_list_enumerates_all_identifiers_deterministically(tmp_path):
    base = _two_app_project(tmp_path)
    records = list_records(base)
    assert [r.identifier for r in records] == [
        "models:blog.post",
        "models:shop.order",
    ]


def test_list_narrows_by_facets(tmp_path):
    base = _two_app_project(tmp_path)
    assert [r.identifier for r in list_records(base, kind="models")] == [
        "models:blog.post",
        "models:shop.order",
    ]
    assert [r.identifier for r in list_records(base, namespace="shop")] == [
        "models:shop.order"
    ]


def _multi_kind_project(tmp_path):
    """Two kinds across two apps, declared so neither kind is the whole store."""
    views_body = MODELS_BODY.replace("models", "views").replace("Post", "Page")
    return project(
        tmp_path,
        framework_body='import spoc\nframework = spoc.Framework("models", "views")\n',
        apps={
            "shop": {
                "models": MODELS_BODY.replace("Post", "Order"),
                "views": views_body.replace("Page", "Cart"),
            },
            "blog": {"models": MODELS_BODY, "views": views_body},
        },
    )


def test_list_narrowed_to_a_kind_reports_that_kind_in_canonical_order(tmp_path):
    """Narrowing reads one facet, and takes the facet's own order.

    The facet is read rather than filtered out of the whole store, so this also
    pins that the ordering survives the change of reader: records arrive in
    canonical identifier order without the listing sorting them again.
    """
    base = _multi_kind_project(tmp_path)

    models = [r.identifier for r in list_records(base, kind="models")]
    views = [r.identifier for r in list_records(base, kind="views")]

    assert models == ["models:blog.post", "models:shop.order"]
    assert views == ["views:blog.page", "views:shop.cart"]
    # Canonical order, and no record of the other kind reached the result.
    assert models == sorted(models)
    assert views == sorted(views)
    assert not {r.split(":")[0] for r in models} & {r.split(":")[0] for r in views}


def test_list_narrowing_composes_kind_and_namespace(tmp_path):
    base = _multi_kind_project(tmp_path)

    assert [
        r.identifier for r in list_records(base, kind="views", namespace="shop")
    ] == ["views:shop.cart"]


def test_list_namespace_narrowing_matching_nothing_is_empty_not_an_error(tmp_path):
    """Namespaces are an open set, so an unknown one has no candidates to name."""
    base = _multi_kind_project(tmp_path)

    assert list_records(base, namespace="nowhere") == []
    assert list_records(base, kind="models", namespace="nowhere") == []


def test_list_unknown_kind_names_the_valid_kinds(tmp_path, capsys):
    base = project(tmp_path)
    with pytest.raises(Exception, match="models"):
        list_records(base, kind="controllers")
    assert cli_main(["list", str(base), "--kind", "controllers"]) == 1
    assert "models" in capsys.readouterr().err


def test_list_cli_prints_identifiers(tmp_path, capsys):
    base = _two_app_project(tmp_path)
    assert cli_main(["list", str(base)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["models:blog.post", "models:shop.order"]


# ── explain ───────────────────────────────────────────────────────────────


def test_explain_known_identifier(tmp_path, capsys):
    base = project(tmp_path)
    record = explain("models:blog.post", base)
    assert (record.kind, record.namespace, record.object_name) == (
        "models",
        "blog",
        "post",
    )
    assert record.location == "blog.models:Post"

    assert cli_main(["explain", "models:blog.post", str(base)]) == 0
    out = capsys.readouterr().out
    assert "models:blog.post" in out and "blog.models:Post" in out


def test_explain_unknown_identifier_fails_with_candidates(tmp_path, capsys):
    base = project(tmp_path)
    assert cli_main(["explain", "models:blog.pist", str(base)]) == 1
    err = capsys.readouterr().err
    assert "pist" in err and "post" in err


# ── framework location ────────────────────────────────────────────────────


def test_generated_convention_needs_no_flags(tmp_path):
    """The default ref is exactly what `spoc init` emits."""
    base = project(tmp_path)
    assert check(base).ok


def test_framework_override_for_custom_layouts(tmp_path):
    base = project(tmp_path, framework_body=None)
    (base / "myfw.py").write_text(
        SYNC_FRAMEWORK.replace("framework =", "app_framework ="), encoding="utf-8"
    )
    assert check(base, "myfw:app_framework").ok
    assert [r.identifier for r in list_records(base, "myfw:app_framework")] == [
        "models:blog.post"
    ]


def test_missing_declaration_is_actionable(tmp_path, capsys):
    base = project(tmp_path, framework_body=None)
    report = check(base)
    assert [f.area for f in report.findings] == ["locate"]
    assert "framework:framework" in report.findings[0].message
    assert "--framework" in report.findings[0].message

    assert cli_main(["list", str(base)]) == 1
    assert "--framework" in capsys.readouterr().err


def test_ref_not_a_framework_is_refused(tmp_path):
    base = project(tmp_path, framework_body="framework = 42\n")
    with pytest.raises(LocateError, match="not a Framework"):
        list_records(base)


def test_malformed_ref_is_refused(tmp_path):
    base = project(tmp_path)
    with pytest.raises(LocateError, match="module:attribute"):
        list_records(base, "no-colon-here")


# ── containment boundary ──────────────────────────────────────────────────


def test_no_kernel_module_imports_the_diagnostics():
    """Kernel modules never import the diagnostics surface (`spoc.cli` is the
    composed console adapter, not kernel — it is the one allowed importer)."""
    root = Path(__file__).parent.parent / "src/spoc"
    for path in sorted(root.rglob("*.py")):
        if (root / "diagnostics") in path.parents or path == root / "cli.py":
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
                assert "diagnostics" not in name.split("."), f"{path.name}: {name}"


def test_importing_spoc_never_loads_diagnostics_or_cli():
    code = (
        "import sys; import spoc; "
        "print([m for m in sys.modules "
        "if m.startswith('spoc.diagnostics') or m == 'spoc.cli'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"
