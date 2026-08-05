"""
The filesystem adapter: stage, verify, commit.

Every file in a plan is written into a temporary directory first and only moved
into place once all of them exist. A failure mid-write therefore leaves the
destination untouched rather than half-populated, which is what the specs demand
and what a naive write-as-you-go loop cannot promise.

``os.replace`` is atomic within a filesystem; the staging directory is created
beside the destination so the move stays on one.
"""

import os
import shutil
import tempfile
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path

from .errors import PathEscapeError, TargetNotEmptyError
from .plan import GenerationPlan


class DirectorySink:
    """
    Writes a plan into a destination directory.

    Implements the :class:`~spoc.scaffold.plan.ProjectSink` port.
    """

    def __init__(self, destination: Path) -> None:
        self.destination = destination

    def location(self) -> str:
        return str(self.destination)

    def is_empty(self) -> bool:
        if not self.destination.exists():
            return True
        return not any(self.destination.iterdir())

    def existing(self, paths: Sequence[str]) -> tuple[str, ...]:
        return tuple(p for p in paths if (self.destination / p).exists())

    def commit(self, plan: GenerationPlan) -> None:
        """Write every file in the plan, or none of them.

        The never-overwrite guarantee is enforced here, not left to callers:
        a non-empty destination is refused before anything is staged.
        """
        if not self.is_empty():
            raise TargetNotEmptyError(self.location())
        parent = self.destination.parent
        parent.mkdir(parents=True, exist_ok=True)

        staging = Path(tempfile.mkdtemp(prefix=".spoc-scaffold-", dir=parent))
        try:
            for planned in plan:
                self._write_staged(staging, planned.path, planned.content)
            self._commit_staged(staging)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def _write_staged(self, staging: Path, relative: str, content: str) -> None:
        """Write one file inside the staging root, refusing to escape it."""
        target = (staging / relative).resolve()
        if not target.is_relative_to(staging.resolve()):
            raise PathEscapeError(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def _commit_staged(self, staging: Path) -> None:
        """Move the staged tree into the destination."""
        if not self.destination.exists():
            # One atomic move: the staged tree becomes the destination. The
            # caller's rmtree then finds nothing, which ignore_errors handles.
            os.replace(staging, self.destination)
            return

        try:
            # The destination exists but is empty (is_empty gated the operation):
            # remove it so the whole-tree move stays the single atomic step.
            os.rmdir(self.destination)
        except OSError:
            # The directory cannot be swapped out (it is the working directory,
            # say) — move per file, undoing the moves if any one of them fails.
            self._move_files_with_rollback(staging)
        else:
            try:
                os.replace(staging, self.destination)
            except BaseException:
                # The destination was removed only to make room for the move. If
                # the move did not happen, put the empty directory back — a failed
                # commit leaves what it found, and it found a directory.
                with suppress(OSError):
                    self.destination.mkdir(parents=True, exist_ok=True)
                raise

    def _move_files_with_rollback(self, staging: Path) -> None:
        moved: list[Path] = []
        created_dirs: list[Path] = []
        try:
            for staged in sorted(staging.rglob("*")):
                if staged.is_dir():
                    continue
                relative = staged.relative_to(staging)
                final = self.destination / relative
                parent = final.parent
                while not parent.exists() and parent != self.destination:
                    created_dirs.append(parent)
                    parent = parent.parent
                final.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, final)
                moved.append(final)
        except BaseException:
            # Best-effort restoration to emptiness: the files we moved, then the
            # directories we created for them, deepest first.
            for final in moved:
                with suppress(OSError):
                    final.unlink()
            for directory in sorted(created_dirs, reverse=True):
                with suppress(OSError):
                    directory.rmdir()
            raise
