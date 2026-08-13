"""Reading the withdrawal mark out of source, without executing anything.

Griffe never supplies this: `Object.deprecated` is assigned only by its JSON
decoder, and `BreakageKind` has no deprecation member — so the mark is read from
a syntax tree here. These tests write tiny packages to disk and read them back,
which is the only way to exercise a spelling this repository does not yet use.

The reproduction test at the end is the one that matters most: it runs against
this repository's real source and pins the one withdrawal actually in flight.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from apicheck import extract
from apicheck.core import Kind

# tests -> apicheck -> tools -> py -> scripts -> repo root
REPO = Path(__file__).resolve().parents[5]

ALIAS_MARK = """
from spoc.core.deprecation import deprecated_alias
from . import archive

thing = deprecated_alias(
    archive.thing,
    "pkg.thing is deprecated; import it from "
    "pkg.archive instead. Removed at 1.0.",
)

__all__ = ["thing"]
"""

DECORATOR_MARK = '''
from spoc.core.deprecation import deprecated


@deprecated("pkg.Widget is deprecated; use pkg.Gadget instead.")
def Widget():
    """A widget."""


__all__ = ["Widget"]
'''


@pytest.fixture
def package(tmp_path: Path):
    """Write a one-module package and return its source root."""

    def build(body: str, *, extra: dict[str, str] | None = None) -> Path:
        root = tmp_path / "src"
        pkg = root / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text(body, encoding="utf-8")
        (pkg / "archive.py").write_text(
            "def thing():\n    'The real one.'\n", encoding="utf-8"
        )
        for name, text in (extra or {}).items():
            (pkg / name).write_text(text, encoding="utf-8")
        return root

    return build


def withdrawn(exposures):
    return {e.element: e.withdrawal for e in exposures if e.withdrawal}


# --- the two sanctioned spellings ---------------------------------------


def test_a_withdrawn_re_export_is_read_with_its_notice(package):
    root = package(ALIAS_MARK)
    marks = withdrawn(extract.exposures(root, "pkg"))

    assert "pkg.thing" in marks
    assert marks["pkg.thing"].replacement_stated is True


def test_a_notice_split_across_literals_is_recovered_whole(package):
    """The reason this reads a syntax tree and not a pattern.

    The notice is two adjacent literals in the source; a reader that took the
    first one would judge the notice on half its text.
    """
    root = package(ALIAS_MARK)
    message = withdrawn(extract.exposures(root, "pkg"))["pkg.thing"].message

    assert message.endswith("Removed at 1.0.")
    assert "pkg.archive instead" in message


def test_a_withdrawn_definition_is_read_from_its_decorator(package):
    root = package(DECORATOR_MARK)
    marks = withdrawn(extract.exposures(root, "pkg"))

    assert "pkg.Widget" in marks
    assert "use pkg.Gadget instead" in marks["pkg.Widget"].message


def test_an_unmarked_element_carries_no_withdrawal(package):
    root = package('def thing():\n    "A thing."\n\n\n__all__ = ["thing"]\n')
    assert withdrawn(extract.exposures(root, "pkg")) == {}


def test_a_withdrawn_element_keeps_its_tier(package):
    """Read beside the tier, never instead of it."""
    from apicheck.core import Tier, derive_tier

    root = package(ALIAS_MARK)
    thing = next(e for e in extract.exposures(root, "pkg") if e.element == "pkg.thing")

    assert derive_tier(thing) is Tier.PUBLIC
    assert thing.withdrawal is not None


# --- a mark spelled some other way --------------------------------------


def test_a_hand_rolled_signal_is_reported_as_unsanctioned(package):
    """The escape hatch that would otherwise read as "not withdrawn"."""
    root = package(
        "__all__ = []\n",
        extra={
            "rogue.py": (
                "import warnings\n\n\n"
                "def old():\n"
                '    warnings.warn("old is deprecated", DeprecationWarning)\n'
            )
        },
    )
    findings = extract.unsanctioned_marks(root, "pkg")

    assert [f.kind for f in findings] == [Kind.UNSANCTIONED]
    assert findings[0].element.startswith("pkg.rogue:")
    assert findings[0].fatal is True


def test_a_signal_raised_by_the_sanctioned_module_is_not_reported(tmp_path: Path):
    """The one module allowed to raise it must not report itself."""
    root = tmp_path / "src"
    module = root / "spoc" / "core"
    module.mkdir(parents=True)
    (root / "spoc" / "__init__.py").write_text("", encoding="utf-8")
    (module / "__init__.py").write_text("", encoding="utf-8")
    (module / "deprecation.py").write_text(
        "import warnings\n\n\n"
        "def mark(message):\n"
        "    warnings.warn(message, category=DeprecationWarning)\n",
        encoding="utf-8",
    )

    assert extract.unsanctioned_marks(root, "spoc") == []


def test_an_unparseable_module_is_a_gap_not_a_clean_bill(package):
    """ "Could not read" must never be reported as "carries no mark"."""
    root = package("__all__ = []\n", extra={"broken.py": "def (\n"})
    findings = extract.unsanctioned_marks(root, "pkg")

    assert [f.kind for f in findings] == [Kind.UNVERIFIABLE]
    assert findings[0].fatal is False


# --- against the real repository ----------------------------------------


def test_every_live_withdrawal_in_this_repository_states_its_replacement():
    """Whatever is in the lifecycle right now, read end to end.

    The set is empty today: `spoc.scaffold.extract_archive` completed its
    withdrawal at 1.0 and nothing has entered the lifecycle since. Asserted as a
    property of the set rather than against a named element, so the next real
    deprecation is checked here the moment it lands instead of failing this test
    merely by existing.
    """
    marks = withdrawn(extract.exposures(REPO / "src"))

    assert all(mark.replacement_stated for mark in marks.values())


def test_this_repository_raises_no_unsanctioned_signal():
    assert extract.unsanctioned_marks(REPO / "src") == []
