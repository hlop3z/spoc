"""
Reference grammar tests: one per scenario in `remote-template-acquisition`'s
"Every reference resolves by one ordered, total rule".

Every test here is a pure function call. The grammar decides what a reference
*means* without consulting a disk or a network, so none of these touch either —
that is the property under test as much as the parse results are.
"""

from pathlib import Path
from typing import ClassVar

import pytest

from spoc.scaffold.core import RECOGNIZED_FORMS, parse_reference
from spoc.scaffold.errors import UnrecognizedReferenceError
from spoc.scaffold.plan import ReferenceKind


class TestBareNames:
    def test_builtin_name_is_a_name(self) -> None:
        ref = parse_reference("default")
        assert ref.kind is ReferenceKind.NAME
        assert ref.location == "default"
        assert ref.revision is None

    def test_name_is_not_pinned(self) -> None:
        assert parse_reference("default").is_pinned is False

    def test_surrounding_whitespace_is_ignored(self) -> None:
        assert parse_reference("  default  ").location == "default"


class TestPaths:
    @pytest.mark.parametrize(
        "spelling",
        ["./mytemplates", "../shared/sets", "mytemplates/nested", r".\mytemplates"],
    )
    def test_separator_makes_it_a_path(self, spelling: str) -> None:
        ref = parse_reference(spelling)
        assert ref.kind is ReferenceKind.PATH
        assert ref.location == spelling

    @pytest.mark.parametrize(
        "spelling", [r"C:\templates", "C:/templates", r"d:\a\b", "Z:/x"]
    )
    def test_drive_letter_is_a_path_not_a_scheme(self, spelling: str) -> None:
        """The ordering that makes this pass is the point — a drive letter
        satisfies the scheme grammar, and losing that race would make every
        absolute Windows path an unrecognized scheme."""
        ref = parse_reference(spelling)
        assert ref.kind is ReferenceKind.PATH
        assert ref.scheme == ""
        assert ref.location == spelling


class TestRemoteForms:
    def test_gh_shorthand(self) -> None:
        ref = parse_reference("gh:owner/repo")
        assert ref.kind is ReferenceKind.REMOTE
        assert ref.scheme == "gh"
        assert ref.location == "owner/repo"

    def test_gh_shorthand_with_revision(self) -> None:
        ref = parse_reference("gh:owner/repo@v1.2")
        assert ref.location == "owner/repo"
        assert ref.revision == "v1.2"
        assert ref.is_pinned is True

    def test_subdirectory_fragment(self) -> None:
        ref = parse_reference("gh:owner/repo@v1.2#subdirectory=templates/minimal")
        assert ref.location == "owner/repo"
        assert ref.revision == "v1.2"
        assert ref.subdirectory == "templates/minimal"

    def test_subdirectory_without_revision(self) -> None:
        ref = parse_reference("gh:owner/repo#subdirectory=sets/small")
        assert ref.revision is None
        assert ref.subdirectory == "sets/small"

    def test_https_archive(self) -> None:
        ref = parse_reference("https://host/o/r/archive/v1.tar.gz")
        assert ref.kind is ReferenceKind.REMOTE
        assert ref.scheme == "https"
        assert ref.location == "//host/o/r/archive/v1.tar.gz"

    def test_scheme_is_lowercased(self) -> None:
        assert parse_reference("HTTPS://host/a.tar.gz").scheme == "https"

    def test_vcs_scheme(self) -> None:
        ref = parse_reference("git+https://host/owner/repo@v2")
        assert ref.kind is ReferenceKind.REMOTE
        assert ref.scheme == "git+https"
        assert ref.revision == "v2"

    def test_userinfo_at_is_not_a_revision(self) -> None:
        """`git@host` carries an `@` before the final `/`; only an `@` after it
        can be a revision, or every ssh-style reference would parse a bogus pin."""
        ref = parse_reference("git+ssh://git@host/owner/repo")
        assert ref.revision is None
        assert ref.location == "//git@host/owner/repo"

    def test_userinfo_and_revision_together(self) -> None:
        ref = parse_reference("git+ssh://git@host/owner/repo@v3")
        assert ref.revision == "v3"
        assert ref.location == "//git@host/owner/repo"

    def test_fragment_is_stripped_before_revision(self) -> None:
        """A fragment can contain both `/` and `@`; leaving it attached would
        corrupt the revision split."""
        ref = parse_reference("gh:owner/repo#subdirectory=a@b/c")
        assert ref.revision is None
        assert ref.subdirectory == "a@b/c"

    def test_unknown_fragment_parameter_is_ignored(self) -> None:
        ref = parse_reference("gh:owner/repo#egg=something")
        assert ref.subdirectory is None


class TestRefusals:
    def test_unknown_scheme_is_refused(self) -> None:
        with pytest.raises(UnrecognizedReferenceError) as caught:
            parse_reference("ftp://host/x.tar.gz")
        assert "ftp" in str(caught.value)

    def test_scheme_bearing_reference_never_becomes_a_path(self) -> None:
        """The whole reason resolution is scheme-first: a mistyped scheme carries
        separators, and under the old separator-first heuristic it would have been
        read as a directory nobody named. It must raise instead."""
        with pytest.raises(UnrecognizedReferenceError):
            parse_reference("gh:/owner/repo".replace("gh:", "gitlab:"))

    def test_recognized_scheme_wins_over_a_same_spelled_local_path(self) -> None:
        """Form is decided before existence is consulted — a reference whose form
        says remote stays remote whatever sits on disk under that spelling."""
        ref = parse_reference("gh:owner/repo")
        assert ref.kind is ReferenceKind.REMOTE

    def test_empty_reference_is_refused(self) -> None:
        with pytest.raises(UnrecognizedReferenceError):
            parse_reference("   ")

    def test_scheme_without_location_is_refused(self) -> None:
        with pytest.raises(UnrecognizedReferenceError) as caught:
            parse_reference("gh:")
        assert "names no location" in str(caught.value)

    def test_refusal_lists_the_recognized_forms(self) -> None:
        with pytest.raises(UnrecognizedReferenceError) as caught:
            parse_reference("ftp://host/x")
        message = str(caught.value)
        for form in RECOGNIZED_FORMS:
            assert form in message

    def test_refusal_states_nothing_was_written(self) -> None:
        with pytest.raises(UnrecognizedReferenceError) as caught:
            parse_reference("ftp://host/x")
        assert "Nothing was written" in str(caught.value)


class TestDocumentedFormsParse:
    """Every `--template` form the docs show must parse to what they claim.

    The remote examples name placeholder repositories, so they cannot be
    executed against a real host — but they can be parsed, and a documented
    spelling the parser rejects is exactly the drift this guards against.
    """

    DOCUMENTED: ClassVar[dict[str, ReferenceKind]] = {
        "default": ReferenceKind.NAME,
        "./mytemplates": ReferenceKind.PATH,
        r"C:\templates": ReferenceKind.PATH,
        "gh:owner/repo": ReferenceKind.REMOTE,
        "https://host/sets.tar.gz": ReferenceKind.REMOTE,
        "gh:owner/repo@v1.2": ReferenceKind.REMOTE,
        "gh:owner/repo@v1.2#subdirectory=templates/minimal": ReferenceKind.REMOTE,
        "git+https://gitlab.com/owner/repo@v1.2": ReferenceKind.REMOTE,
    }

    @pytest.mark.parametrize("spelling", sorted(DOCUMENTED))
    def test_documented_form_parses_to_the_documented_kind(self, spelling: str) -> None:
        assert parse_reference(spelling).kind is self.DOCUMENTED[spelling]

    def test_documented_pin_and_subdirectory_mean_what_the_docs_say(self) -> None:
        ref = parse_reference("gh:owner/repo@v1.2#subdirectory=templates/minimal")
        assert ref.revision == "v1.2"
        assert ref.subdirectory == "templates/minimal"

    def test_every_documented_template_example_is_covered(self) -> None:
        """Reads the page itself, so a new example added to the docs without a
        parse expectation here fails rather than going unchecked."""
        page = Path("docs/docs/tools/cli.md").read_text(encoding="utf-8")
        used = {
            line.split("--template", 1)[1].strip()
            for line in page.splitlines()
            if "--template " in line and line.strip().startswith("spoc ")
        }
        assert used, "the page should still show --template examples"
        assert used <= set(self.DOCUMENTED), (
            f"undocumented in tests: {used - set(self.DOCUMENTED)}"
        )


class TestTotality:
    @pytest.mark.parametrize(
        "spelling",
        [
            "default",
            "./local",
            r"C:\templates",
            "gh:o/r",
            "https://h/a.tar.gz",
            "git+https://h/o/r@v1",
        ],
    )
    def test_every_recognized_form_yields_a_reference(self, spelling: str) -> None:
        ref = parse_reference(spelling)
        assert ref.kind in ReferenceKind
        assert ref.raw == spelling

    def test_raw_is_preserved_for_errors(self) -> None:
        assert parse_reference("  gh:o/r  ").raw == "gh:o/r"
