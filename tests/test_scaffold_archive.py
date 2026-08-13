"""
Archive admission tests: the trust boundary for retrieved template sets.

One test per refusal scenario in `remote-template-acquisition`, plus the
layering check that matters most — that containment still holds when the
standard library's extraction filter is bypassed. Every archive here is built in
memory; nothing reaches the network.
"""

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from spoc.scaffold import archive as archive_module
from spoc.scaffold.archive import (
    MAX_EXPANDED_BYTES,
    MAX_MEMBERS,
    extract_archive,
)
from spoc.scaffold.errors import BoundExceededError, MemberRefusedError


def _tar(members: list[tuple[str, bytes]], *, kind: str = "reg") -> bytes:
    """Build a tar carrying exactly the members named, including illegal ones."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, payload in members:
            info = tarfile.TarInfo(name)
            if kind == "link":
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                archive.addfile(info)
                continue
            info.size = len(payload)
            info.type = tarfile.REGTYPE
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def _zip(members: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in members:
            archive.writestr(name, payload)
    return buffer.getvalue()


class TestAdmission:
    def test_ordinary_archive_lands(self, tmp_path: Path) -> None:
        extract_archive(_tar([("a/manifest.toml", b"x = 1")]), tmp_path)
        assert (tmp_path / "a" / "manifest.toml").read_text() == "x = 1"

    def test_traversing_member_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MemberRefusedError) as caught:
            extract_archive(_tar([("../evil.txt", b"pwned")]), tmp_path)
        assert "evil.txt" in str(caught.value)
        assert not (tmp_path.parent / "evil.txt").exists()

    def test_absolute_member_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MemberRefusedError):
            extract_archive(_tar([("/tmp/evil.txt", b"pwned")]), tmp_path)

    def test_symlink_member_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MemberRefusedError) as caught:
            extract_archive(_tar([("link", b"")], kind="link"), tmp_path)
        assert "link" in str(caught.value)

    def test_refusal_creates_nothing_outside(self, tmp_path: Path) -> None:
        """A refused member must not leave a directory behind — the containment
        check runs before anything is created, not after."""
        outside = tmp_path.parent / "escaped_dir"
        with pytest.raises(MemberRefusedError):
            extract_archive(_tar([("../escaped_dir/f.txt", b"x")]), tmp_path)
        assert not outside.exists()

    def test_unrecognized_format_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MemberRefusedError) as caught:
            extract_archive(b"this is not an archive", tmp_path)
        assert "not a recognized archive format" in str(caught.value)

    def test_format_is_decided_by_content_not_name(self, tmp_path: Path) -> None:
        """Nothing the remote party says names the format; only the bytes do."""
        extract_archive(_zip([("a/manifest.toml", b"x = 1")]), tmp_path)
        assert (tmp_path / "a" / "manifest.toml").exists()


class TestFilterIsNotTrustedAlone:
    """The last line of defense, tested with every earlier line removed.

    CVE-2025-4517 was a traversal bypass *inside* `filter="data"`, patched only
    in 3.12.11 / 3.13.4 while this project's floor is 3.12 — so a supported
    interpreter may ship a filter that admits what these tests feed it. Both
    earlier controls are stubbed to pass everything, leaving only the
    containment re-check. If these tests pass, that layer alone is sufficient.
    """

    @staticmethod
    def _disable_earlier_layers(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(tarfile, "data_filter", lambda member, path: member)
        monkeypatch.setattr(archive_module, "_is_unsafe_name", lambda name: False)

    def test_containment_holds_when_every_earlier_layer_is_bypassed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._disable_earlier_layers(monkeypatch)

        with pytest.raises(MemberRefusedError) as caught:
            extract_archive(_tar([("../bypassed.txt", b"pwned")]), tmp_path)

        assert "outside the destination" in str(caught.value)
        assert not (tmp_path.parent / "bypassed.txt").exists()

    def test_common_prefix_sibling_is_refused_when_bypassed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Django's CVE-2025-59682: a sibling sharing a leading string with the
        destination is not contained by it. `is_relative_to` compares components,
        so this is refused where a `startswith` check would admit it."""
        self._disable_earlier_layers(monkeypatch)

        destination = tmp_path / "target"
        destination.mkdir()

        with pytest.raises(MemberRefusedError):
            extract_archive(_tar([("../target_evil/f.txt", b"pwned")]), destination)
        assert not (tmp_path / "target_evil").exists()

    def test_zip_containment_holds_when_bypassed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._disable_earlier_layers(monkeypatch)

        with pytest.raises(MemberRefusedError):
            extract_archive(_zip([("../bypassed.txt", b"pwned")]), tmp_path)
        assert not (tmp_path.parent / "bypassed.txt").exists()


class TestBounds:
    """Bounds are exercised against small injected limits; the shipped defaults
    are asserted separately so both the mechanism and the value stay covered."""

    def test_shipped_bounds_are_sane(self) -> None:
        assert MAX_EXPANDED_BYTES >= 16 * 1024 * 1024
        assert MAX_MEMBERS >= 1000

    def test_member_count_bound_is_enforced(self, tmp_path: Path) -> None:
        members = [(f"f{n}.txt", b"x") for n in range(12)]
        with pytest.raises(BoundExceededError) as caught:
            extract_archive(_tar(members), tmp_path, max_members=10)
        assert "member count" in str(caught.value)

    def test_expanded_size_bound_is_enforced(self, tmp_path: Path) -> None:
        """The bound is on expanded size, not transferred size — this archive
        compresses to almost nothing and expands well past the limit."""
        payload = b"\0" * (4 * 1024 * 1024)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            info = tarfile.TarInfo("bomb.bin")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        compressed = buffer.getvalue()

        assert len(compressed) < 64 * 1024, "the bomb should be small on the wire"

        with pytest.raises(BoundExceededError) as caught:
            extract_archive(compressed, tmp_path, max_expanded=1024 * 1024)
        assert "expanded size" in str(caught.value)

    def test_bound_halts_before_the_whole_member_lands(self, tmp_path: Path) -> None:
        """Halting *at* the bound rather than after it is the point — otherwise
        the bomb has already landed by the time the limit is noticed."""
        limit = 512 * 1024
        payload = b"\0" * (8 * 1024 * 1024)
        with pytest.raises(BoundExceededError):
            extract_archive(_tar([("bomb.bin", payload)]), tmp_path, max_expanded=limit)

        landed = sum(f.stat().st_size for f in tmp_path.rglob("*") if f.is_file())
        assert landed <= limit + 64 * 1024, "expansion should stop near the bound"

    def test_zip_bound_ignores_the_declared_size(self, tmp_path: Path) -> None:
        """`file_size` is declared by the archive and can understate; the bound is
        enforced on bytes as they actually land."""
        payload = b"\0" * (4 * 1024 * 1024)
        with pytest.raises(BoundExceededError):
            extract_archive(
                _zip([("bomb.bin", payload)]), tmp_path, max_expanded=1024 * 1024
            )


class TestZipMembers:
    def test_traversing_zip_member_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MemberRefusedError):
            extract_archive(_zip([("../evil.txt", b"pwned")]), tmp_path)

    def test_absolute_zip_member_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MemberRefusedError):
            extract_archive(_zip([("/tmp/evil.txt", b"pwned")]), tmp_path)

    def test_drive_qualified_zip_member_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MemberRefusedError):
            extract_archive(_zip([("C:/evil.txt", b"pwned")]), tmp_path)


class TestWithdrawalCompleted:
    """The re-export is gone; the definition it pointed at is not.

    This is the element the deprecation lifecycle was exercised on — deprecated
    in 0.6.0, still working through 0.7.0 and 0.8.0, removed at 1.0. Both halves
    are asserted because a withdrawal is only honest if the spelling the warning
    named still works: the promise ended, the capability did not.
    """

    def test_the_package_spelling_is_gone(self) -> None:
        import spoc.scaffold

        assert not hasattr(spoc.scaffold, "extract_archive")
        assert "extract_archive" not in spoc.scaffold.__all__

    def test_the_submodule_spelling_still_admits(self, tmp_path: Path) -> None:
        archive_module.extract_archive(_tar([("a.txt", b"x")]), tmp_path)
        assert (tmp_path / "a.txt").read_text() == "x"
