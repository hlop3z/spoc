"""
The gate that proves the feature works: three type checkers read one generated
stub and must agree about what it promises.

Why three. `ty` is this project's own checker but is beta at 0.0.x and runs in
nobody's editor, so a stub could pass CI and fail every user. pyright is the
engine behind Pylance, which makes it the authority on the autocomplete claim.
mypy is the independent third reading. A disagreement between them is a finding
about the stub, never something to resolve by loosening it.

These tests shell out to real checkers, so they are the slowest in the suite.
That cost is the point: nothing cheaper actually demonstrates that a developer
gets completion.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from spoc.stubs import generate, verify

FIXTURE = Path(__file__).parent / "conformance"

#: Checkers verified against this fixture. Recorded so a future regression is
#: traceable to a version bump rather than to the stub itself.
VERIFIED_VERSIONS = {"mypy": "2.3.0", "pyright": "1.1.411", "ty": "0.0.66"}


def _run(module: str, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env={**_env(), "MYPYPATH": str(cwd)},
    )


def _env() -> dict[str, str]:
    import os

    return dict(os.environ)


def check_mypy(cwd: Path, target: str) -> subprocess.CompletedProcess[str]:
    return _run("mypy", ["--no-incremental", "--no-error-summary", target], cwd)


def check_pyright(cwd: Path, *targets: str) -> subprocess.CompletedProcess[str]:
    # The interpreter is named explicitly. Pyright otherwise looks for a virtual
    # environment beside its project root — which here is the fixture directory,
    # not the repository — and falls back to whichever `python` is on PATH. That
    # one has no `spoc` installed, so every assertion would fail with `Unknown`
    # unless the venv happened to be activated in the calling shell.
    return _run("pyright", ["--pythonpath", sys.executable, *targets], cwd)


def check_ty(cwd: Path, target: str) -> subprocess.CompletedProcess[str]:
    return _run("ty", ["check", "--extra-search-path", ".", target], cwd)


# ── The committed stub is current ─────────────────────────────────────────


def test_committed_fixture_stub_is_current():
    """If this fails, the fixture changed and its stub was not regenerated —
    which would make every assertion below test a stale artifact."""
    report = verify(FIXTURE)
    assert report.ok, report.reason


def test_the_fixture_exercises_every_shape_and_a_degraded_entry():
    report = verify(FIXTURE)
    assert report.entries == 5
    assert report.degraded == 1, "the fixture must keep one honestly-degraded entry"


def test_the_fixture_app_is_nested_under_a_container_package():
    """Nesting apps under a container directory is what projects do past a
    handful of apps, and it is the layout where the emitter's module-path
    aliasing earns its keep — `apps.shop.models.Product` must alias distinctly
    while the identifier stays `models:shop.product`. Flattening the fixture
    would leave that untested, so the layout is asserted rather than assumed."""
    assert (FIXTURE / "apps" / "shop" / "models.py").is_file()
    stub = (FIXTURE / "framework.pyi").read_text(encoding="utf-8")
    assert "from apps.shop.models import Product as _apps_shop_models_Product" in stub
    assert '"models:shop.product"' in stub


# ── All three checkers agree ──────────────────────────────────────────────


def test_mypy_accepts_the_generated_stub():
    result = check_mypy(FIXTURE, "assertions.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_ty_accepts_the_generated_stub():
    result = check_ty(FIXTURE, "assertions.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_pyright_accepts_the_generated_stub():
    result = check_pyright(FIXTURE, "assertions.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_pyright_renders_the_types_a_hover_would_show():
    """Pylance is pyright, so the rendered text is the editor experience."""
    result = check_pyright(FIXTURE, "hover_pyright.py")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("module", sorted(VERIFIED_VERSIONS))
def test_checker_versions_are_recorded(module):
    """Not a pin — a record. A conformance failure after an upgrade should be
    attributable to the upgrade without archaeology."""
    result = subprocess.run(
        [sys.executable, "-m", module, "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert VERIFIED_VERSIONS[module] in result.stdout, (
        f"{module} is now {result.stdout.strip()}, recorded "
        f"{VERIFIED_VERSIONS[module]}; re-run the conformance gate and update "
        "VERIFIED_VERSIONS if it still passes"
    )


# ── Strict mode turns a misspelling into a type error ─────────────────────


TYPO_PROBE = """
from framework import framework

record = framework.resolve("models:shop.prodcut")
"""


@pytest.fixture
def strict_project(tmp_path):
    """A copy of the fixture with a strict stub and one misspelled identifier."""
    base = tmp_path / "conformance"
    shutil.copytree(FIXTURE, base)
    (base / "assertions.py").unlink()
    (base / "hover_pyright.py").unlink()
    generate(base, strict=True)
    (base / "probe.py").write_text(TYPO_PROBE, encoding="utf-8")
    return base


@pytest.fixture
def permissive_project(tmp_path):
    """The same, but with the catch-all overload kept."""
    base = tmp_path / "permissive"
    shutil.copytree(FIXTURE, base)
    (base / "assertions.py").unlink()
    (base / "hover_pyright.py").unlink()
    generate(base, strict=False)
    (base / "probe.py").write_text(TYPO_PROBE, encoding="utf-8")
    return base


def test_strict_mode_rejects_a_misspelled_identifier_everywhere(strict_project):
    """The reason --strict exists. All three must reject it, or the mode only
    protects users of whichever checker happens to catch it."""
    failures = {
        "mypy": check_mypy(strict_project, "probe.py").returncode,
        "pyright": check_pyright(strict_project, "probe.py").returncode,
        "ty": check_ty(strict_project, "probe.py").returncode,
    }
    assert all(code != 0 for code in failures.values()), (
        f"a misspelled identifier went unreported: {failures}"
    )


def test_permissive_mode_accepts_a_misspelled_identifier(permissive_project):
    """The documented cost of the default: a typo falls through to Any."""
    assert check_mypy(permissive_project, "probe.py").returncode == 0
    assert check_pyright(permissive_project, "probe.py").returncode == 0
    assert check_ty(permissive_project, "probe.py").returncode == 0
