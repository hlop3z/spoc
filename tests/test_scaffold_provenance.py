"""
Provenance tests: one per scenario in the `template-provenance` spec.

The record is advisory by design — it makes a later `spoc app` able to notice a
mismatched shape, and it is never allowed to break anything by being absent,
malformed, or deleted.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from spoc.cli import main as cli_main
from spoc.scaffold import (
    DirectorySink,
    TemplateSetNotFoundError,
    UnsatisfiedValueError,
    init_project,
)
from spoc.scaffold.plan import TemplateFile, TemplateSet
from spoc.scaffold.provenance import (
    RECORD_NAME,
    Origin,
    describe_divergence,
    read_origin,
    record_content,
)


class _FixedSource:
    """A source holding one already-resolved set — what remote retrieval yields
    once the reference has been fetched, admitted, and validated."""

    def __init__(self, loaded: TemplateSet) -> None:
        self._loaded = loaded

    def available(self) -> tuple[str, ...]:
        return (self._loaded.name,)

    def load(self, name: str) -> TemplateSet:
        if name != self._loaded.name:
            raise TemplateSetNotFoundError(name, self.available())
        return self._loaded


@pytest.fixture
def project(tmp_path: Path) -> Path:
    assert cli_main(["init", "demo", "--path", str(tmp_path / "demo")]) == 0
    return tmp_path / "demo"


@pytest.fixture
def bare_set(tmp_path: Path) -> Path:
    """A template set that declares no origin record.

    This is the shape any third-party set has unless its author knew to declare
    a file they never asked to own — which is exactly the case the record was
    built to serve.
    """
    root = tmp_path / "bare"
    root.mkdir()
    (root / "only.py.tmpl").write_text("# $project_name\n", encoding="utf-8")
    (root / "manifest.toml").write_text(
        '[template_set]\nname = "bare"\nvalues = ["project_name"]\n\n'
        '[[files]]\nsource = "only.py.tmpl"\ntarget = "only.py"\n',
        encoding="utf-8",
    )
    return root


class TestTheRecord:
    def test_generation_records_its_origin(self, project: Path) -> None:
        assert (project / RECORD_NAME).is_file()

    def test_record_is_readable_as_data(self, project: Path) -> None:
        origin = read_origin(project)
        assert origin is not None
        assert origin.set_name == "default"
        assert origin.reference == "default"

    def test_record_is_listed_among_generated_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cli_main(["init", "demo", "--path", str(tmp_path / "demo")])
        assert RECORD_NAME in capsys.readouterr().out

    def test_a_local_set_records_no_revision(self, project: Path) -> None:
        """Only a set that can move has a revision to record."""
        origin = read_origin(project)
        assert origin is not None
        assert origin.revision == ""

    def test_removing_the_record_leaves_a_runnable_project(self, project: Path) -> None:
        (project / RECORD_NAME).unlink()
        result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        assert "components registered" in result.stdout

    def test_failed_generation_writes_no_record(self, tmp_path: Path) -> None:
        occupied = tmp_path / "demo"
        occupied.mkdir()
        (occupied / "already-here.txt").write_text("x")
        assert cli_main(["init", "demo", "--path", str(occupied)]) == 1
        assert not (occupied / RECORD_NAME).exists()

    def test_a_set_declaring_no_record_still_produces_one(
        self, tmp_path: Path, bare_set: Path
    ) -> None:
        """Emission is the operation's obligation, not the set's."""
        destination = tmp_path / "demo"
        assert (
            cli_main(
                [
                    "init",
                    "demo",
                    "--path",
                    str(destination),
                    "--template",
                    str(bare_set),
                ]
            )
            == 0
        )
        origin = read_origin(destination)
        assert origin is not None
        assert origin.reference == str(bare_set)
        assert origin.set_name == "bare"


class TestTheRecordSurvivesItsValues:
    """The record holds caller-supplied strings, so writing it is serialization.

    A reference is whatever the author typed — a Windows path carries
    backslashes, and nothing forbids a quote. Emitting these without a real
    serializer produced a record that could not be parsed, which `read_origin`
    reports as *no record at all*: the defect hid inside its own degradation.
    """

    @pytest.mark.parametrize(
        "reference",
        [
            r"C:\templates\mine",
            r"C:\temp\new\test",
            'has"quote',
            "gh:owner/repo@abc#subdirectory=t",
            "back\\slash and 'apostrophe'",
        ],
    )
    def test_reference_round_trips_verbatim(
        self, tmp_path: Path, reference: str
    ) -> None:
        (tmp_path / RECORD_NAME).write_text(
            record_content(Origin(reference=reference, revision="", set_name="s")),
            encoding="utf-8",
        )
        origin = read_origin(tmp_path)
        assert origin is not None
        assert origin.reference == reference

    def test_generating_from_a_path_records_that_path(
        self, tmp_path: Path, bare_set: Path
    ) -> None:
        """The end-to-end form of the same defect: on Windows every local
        directory reference contains backslashes."""
        destination = tmp_path / "demo"
        cli_main(
            ["init", "demo", "--path", str(destination), "--template", str(bare_set)]
        )
        origin = read_origin(destination)
        assert origin is not None
        assert origin.reference == str(bare_set)


class TestReadingIsForgiving:
    def test_absent_record_reads_as_none(self, tmp_path: Path) -> None:
        assert read_origin(tmp_path) is None

    def test_malformed_record_reads_as_none(self, tmp_path: Path) -> None:
        """A note nobody can parse must not fail an unrelated operation."""
        (tmp_path / RECORD_NAME).write_text("{not valid,,", encoding="utf-8")
        assert read_origin(tmp_path) is None

    def test_record_without_the_table_reads_as_none(self, tmp_path: Path) -> None:
        """Parseable but the wrong shape — absent, not a failure."""
        (tmp_path / RECORD_NAME).write_text('{"other": {"x": 1}}', encoding="utf-8")
        assert read_origin(tmp_path) is None

    def test_record_that_is_not_an_object_reads_as_none(self, tmp_path: Path) -> None:
        """JSON's top level may be any value; only an object can carry a record."""
        (tmp_path / RECORD_NAME).write_text("[1, 2, 3]", encoding="utf-8")
        assert read_origin(tmp_path) is None


class TestDivergence:
    def test_matching_origin_says_nothing(self) -> None:
        same = Origin("gh:o/r", "abc", "default")
        assert describe_divergence(same, same) is None

    def test_different_reference_is_reported(self) -> None:
        message = describe_divergence(
            Origin("gh:o/r", "abc", "default"),
            Origin("gh:other/x", "def", "default"),
        )
        assert message is not None
        assert "gh:o/r" in message and "gh:other/x" in message

    def test_different_revision_of_the_same_set_is_reported(self) -> None:
        message = describe_divergence(
            Origin("gh:o/r", "abc", "default"),
            Origin("gh:o/r", "zzz", "default"),
        )
        assert message is not None
        assert "abc" in message and "zzz" in message

    def test_absent_revision_on_one_side_is_not_divergence(self) -> None:
        """A local directory legitimately has no revision; reporting that every
        time would train the author to ignore the message."""
        assert (
            describe_divergence(
                Origin("./sets", "abc", "default"), Origin("./sets", "", "default")
            )
            is None
        )

    def test_absent_record_is_reported_as_unknown(self) -> None:
        message = describe_divergence(None, Origin("default", "", "default"))
        assert message is not None
        assert "records no origin" in message


class TestAddAppSurface:
    def test_matching_project_reports_no_divergence(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        capsys.readouterr()
        assert cli_main(["app", "billing", "--path", str(project)]) == 0
        assert "note:" not in capsys.readouterr().out

    def test_project_without_a_record_is_reported(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (project / RECORD_NAME).unlink()
        capsys.readouterr()
        assert cli_main(["app", "billing", "--path", str(project)]) == 0
        out = capsys.readouterr().out
        assert "note:" in out
        assert "records no origin" in out

    def test_divergence_never_prevents_the_app(
        self, project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (project / RECORD_NAME).write_text(
            record_content(Origin("gh:someone/else", "zzz", "other")),
            encoding="utf-8",
        )
        capsys.readouterr()
        assert cli_main(["app", "billing", "--path", str(project)]) == 0
        assert (project / "apps" / "billing" / "__init__.py").is_file()
        out = capsys.readouterr().out
        assert "note:" in out
        # Divergence, not absence — the record parsed and disagreed.
        assert "gh:someone/else" in out


class TestTheSetCannotReachTheRecord:
    """The record describes a template set to a later operation.

    A description its subject can author is not a description — so the values
    leave the substitution vocabulary entirely, and the destination is reserved.
    """

    def test_a_retrieved_set_gets_the_same_record_shape(self, tmp_path: Path) -> None:
        retrieved = TemplateSet(
            name="theirs",
            values=("project_name",),
            files=(
                TemplateFile(
                    source="only.py.tmpl", target="only.py", content="# $project_name\n"
                ),
            ),
            reference="gh:someone/theirs",
            revision="a" * 40,
        )
        destination = tmp_path / "demo"
        init_project(
            source=_FixedSource(retrieved),
            sink=DirectorySink(destination),
            project_name="demo",
            template_set="theirs",
        )

        origin = read_origin(destination)
        assert origin is not None
        assert origin.reference == "gh:someone/theirs"
        assert origin.revision == "a" * 40
        assert origin.set_name == "theirs"
        # Nothing the retrieved set carries reached the record.
        assert "project_name" not in (destination / RECORD_NAME).read_text(
            encoding="utf-8"
        )

    def test_a_set_declaring_the_record_values_is_refused(self, tmp_path: Path) -> None:
        """They left the vocabulary, so asking for one is unsatisfiable — the
        existing refusal, reached by a set written against the old contract."""
        stale = TemplateSet(
            name="stale",
            values=("template_reference",),
            files=(
                TemplateFile(
                    source="t.tmpl", target="out.txt", content="$template_reference"
                ),
            ),
        )
        destination = tmp_path / "demo"
        with pytest.raises(UnsatisfiedValueError) as caught:
            init_project(
                source=_FixedSource(stale),
                sink=DirectorySink(destination),
                project_name="demo",
                template_set="stale",
            )
        assert "template_reference" in str(caught.value)
        assert not destination.exists()


class TestAddingAnAppLeavesTheProjectAlone:
    def test_configuration_is_byte_identical(self, project: Path) -> None:
        """Why the record is its own file: `spoc app` never edits what the
        author owns, so provenance may not live in the configuration."""
        config = project / "config" / "spoc.toml"
        before = config.read_bytes()
        assert cli_main(["app", "billing", "--path", str(project)]) == 0
        assert config.read_bytes() == before

    def test_the_record_is_not_rewritten(self, project: Path) -> None:
        record = project / RECORD_NAME
        before = record.read_bytes()
        assert cli_main(["app", "billing", "--path", str(project)]) == 0
        assert record.read_bytes() == before
