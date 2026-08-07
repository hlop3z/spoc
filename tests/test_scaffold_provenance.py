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
from spoc.scaffold.provenance import (
    RECORD_NAME,
    Origin,
    describe_divergence,
    read_origin,
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    assert cli_main(["init", "demo", "--path", str(tmp_path / "demo")]) == 0
    return tmp_path / "demo"


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


class TestReadingIsForgiving:
    def test_absent_record_reads_as_none(self, tmp_path: Path) -> None:
        assert read_origin(tmp_path) is None

    def test_malformed_record_reads_as_none(self, tmp_path: Path) -> None:
        """A note nobody can parse must not fail an unrelated operation."""
        (tmp_path / RECORD_NAME).write_text(
            "this is not = valid = toml", encoding="utf-8"
        )
        assert read_origin(tmp_path) is None

    def test_record_without_the_table_reads_as_none(self, tmp_path: Path) -> None:
        (tmp_path / RECORD_NAME).write_text("[other]\nx = 1\n", encoding="utf-8")
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
            '[template]\nreference = "gh:someone/else"\nrevision = "zzz"\nset = "other"\n',
            encoding="utf-8",
        )
        capsys.readouterr()
        assert cli_main(["app", "billing", "--path", str(project)]) == 0
        assert (project / "apps" / "billing" / "__init__.py").is_file()
        assert "note:" in capsys.readouterr().out
