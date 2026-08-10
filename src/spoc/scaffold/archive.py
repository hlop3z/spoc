"""
Admitting retrieved archives onto disk.

This is the trust boundary for third-party content. Everything here treats the
archive as hostile, because a remote template set is written by someone the user
may never have met.

Three controls, deliberately layered, because none of them is sufficient alone:

1. **The standard library's extraction filter** (PEP 706 ``filter="data"``) vets
   each member. This is the adopted control — hand-written extraction is what
   produced Django's CVE-2021-3281 and CVE-2025-59682 in this exact feature.
2. **An explicit kind check.** The filter permits some links; the spec does not.
   Only regular files and directories are admitted.
3. **A containment re-check after materialization.** The filter has itself had a
   traversal bypass — CVE-2025-4517, CVSS 9.4, patched in 3.12.11 and 3.13.4 —
   and this project's floor is 3.12, so a supported interpreter may be
   vulnerable and we cannot control a user's patch level. Verifying the resolved
   path after the fact makes that bypass, and any future one, inert.

Bounds are enforced on *expanded* size, never on transferred size: a small
download that expands enormously is the attack, so the transferred length is the
wrong number to check.

Format is decided by content, never by a filename. Nothing the remote party says
is used to build a local path.
"""

import io
import stat
import tarfile
import zipfile
from pathlib import Path
from typing import IO

from .errors import BoundExceededError, MemberRefusedError

#: The most a retrieved archive may expand to. A template set is source text; a
#: set that expands past this is not a template set, it is a decompression bomb.
MAX_EXPANDED_BYTES = 64 * 1024 * 1024

#: The most members a retrieved archive may contain. Bounds member-count
#: exhaustion, which expands to almost nothing but still costs a syscall each.
MAX_MEMBERS = 20_000

#: Read granularity while expanding. Small enough that the size bound halts near
#: the limit rather than after a whole member has landed.
_CHUNK = 64 * 1024

#: Magic bytes, checked against content rather than against any supplied name.
_GZIP_MAGIC = b"\x1f\x8b"
_ZIP_MAGIC = b"PK\x03\x04"


class _Budget:
    """A running expansion budget, checked as bytes land rather than after."""

    def __init__(self, max_expanded: int, max_members: int) -> None:
        self.max_expanded = max_expanded
        self.max_members = max_members
        self.expanded = 0
        self.members = 0

    def admit_member(self) -> None:
        self.members += 1
        if self.members > self.max_members:
            raise BoundExceededError("member count", self.max_members)

    def admit_bytes(self, count: int) -> None:
        self.expanded += count
        if self.expanded > self.max_expanded:
            raise BoundExceededError("expanded size", self.max_expanded)


def extract_archive(
    data: bytes,
    into: Path,
    *,
    max_expanded: int = MAX_EXPANDED_BYTES,
    max_members: int = MAX_MEMBERS,
) -> None:
    """
    Expand a retrieved archive into a directory, admitting each member.

    ``into`` must already exist. On refusal the directory may hold partial
    content — callers stage into a location they then discard, which is why this
    does not attempt its own rollback.

    The bounds are parameters defaulting to the module constants so a test can
    exercise the limit without building a payload the size of the real one. The
    constants remain the single definition of the shipped bound.

    Raises:
        MemberRefusedError: A member may not be materialized.
        BoundExceededError: The archive exceeds a declared bound.
    """
    root = into.resolve()
    budget = _Budget(max_expanded, max_members)

    if data.startswith(_ZIP_MAGIC):
        _extract_zip(data, root, budget)
    elif data.startswith(_GZIP_MAGIC) or _looks_like_tar(data):
        _extract_tar(data, root, budget)
    else:
        raise MemberRefusedError(
            "<archive>", "the content is not a recognized archive format"
        )


def _looks_like_tar(data: bytes) -> bool:
    """Uncompressed tar carries its magic at a fixed offset in the first header."""
    return len(data) > 265 and data[257:262] == b"ustar"


def _verify_contained(path: Path, root: Path, member: str) -> None:
    """Re-check containment after a member has been materialized.

    ``is_relative_to`` compares path *components*, so a sibling directory sharing
    a leading string with the root is not mistaken for a child — that string-prefix
    confusion is Django's CVE-2025-59682. Together with resolving first, this is
    also what neutralizes a bypass in the extraction filter itself.
    """
    try:
        resolved = path.resolve()
    except OSError as exc:  # pragma: no cover - platform-dependent
        raise MemberRefusedError(
            member, f"its path could not be resolved ({exc})"
        ) from exc
    if resolved != root and not resolved.is_relative_to(root):
        raise MemberRefusedError(member, "it resolves outside the destination")


def _extract_tar(data: bytes, root: Path, budget: _Budget) -> None:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for member in archive:
            budget.admit_member()

            # Checked before the filter, because the filter *neutralizes* an
            # absolute path by making it relative rather than refusing it. That
            # is safe but surprising: a template set carrying an absolute member
            # is malformed, and silently relocating it hides that from its author.
            if _is_unsafe_name(member.name):
                raise MemberRefusedError(
                    member.name, "its path is absolute or escapes the destination"
                )

            # The adopted control. It raises on traversal, absolute paths, and
            # dangerous metadata — and it is not trusted to be the last word.
            try:
                vetted = tarfile.data_filter(member, str(root))
            except tarfile.FilterError as exc:
                raise MemberRefusedError(member.name, str(exc)) from exc
            if vetted is None:  # pragma: no cover - filter chose to skip it
                continue

            # Stricter than the filter: the spec admits regular files and
            # directories, and nothing else.
            if not (vetted.isreg() or vetted.isdir()):
                raise MemberRefusedError(
                    vetted.name, "it is neither a regular file nor a directory"
                )

            # Containment is checked before anything is created, so a refused
            # member never leaves a directory behind outside the destination.
            target = root / vetted.name
            _verify_contained(target, root, vetted.name)

            if vetted.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            source = archive.extractfile(vetted)
            if source is None:  # pragma: no cover - isreg implies a payload
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source, target.open("wb") as sink:
                _copy_bounded(source, sink, budget)
            # Again after materializing: the path may have become a link between
            # the two checks, and this is the check the filter cannot bypass.
            _verify_contained(target, root, vetted.name)


def _extract_zip(data: bytes, root: Path, budget: _Budget) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            budget.admit_member()
            name = info.filename

            # No standard filter exists for zip, so the member checks the tar
            # path gets from data_filter are written out here.
            if _is_unsafe_name(name):
                raise MemberRefusedError(
                    name, "its path is absolute or escapes the destination"
                )
            mode = info.external_attr >> 16
            if mode and stat.S_ISLNK(mode):
                raise MemberRefusedError(name, "it is a symbolic link")

            target = root / name
            _verify_contained(target, root, name)

            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as sink:
                # Streamed rather than trusting info.file_size, which the archive
                # declares and can therefore understate.
                _copy_bounded(source, sink, budget)
            _verify_contained(target, root, name)


def _is_unsafe_name(name: str) -> bool:
    """Reject absolute, drive-qualified, and traversing member names.

    Applied to both archive formats, so a member is admitted or refused on the
    same terms whichever container carried it.
    """
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or ".." in normalized.split("/"):
        return True
    return len(normalized) >= 2 and normalized[1] == ":"


def _copy_bounded(source: IO[bytes], sink: IO[bytes], budget: _Budget) -> None:
    """Copy a member, halting the moment the expansion budget is spent.

    The check is inside the loop on purpose: bounding after the copy would mean
    the bomb has already landed by the time the limit is noticed.
    """
    while chunk := source.read(_CHUNK):
        budget.admit_bytes(len(chunk))
        sink.write(chunk)
