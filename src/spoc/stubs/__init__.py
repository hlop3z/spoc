"""
Generated type stubs for a project's resolution surface.

``resolve("models:catalog.product")`` is a string in, an object out, and the
type checker sees nothing on either side. Everything needed to describe that
surface statically is already in the registry; this subpackage collects it and
writes it down.

The artifact is a **stub**, not a module, and that choice is what makes the
whole thing work. A ``.pyi`` never executes, so it can name
``catalog.models.Product`` freely while the apps stay exactly as decoupled at
runtime as they are today — the property the reference app's ``orders`` view is
written to demonstrate. Deleting the stub changes no behavior at all.

Nothing in the kernel imports this package. Like ``scaffold`` and ``formats``,
it is reached through the CLI and depends inward only.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..core.shape import Shape, shape_of
from ..locate import DEFAULT_FRAMEWORK_REF, locate_root
from ..testing import import_state
from .cli import register
from .emit import emit
from .extract import TypeRef, alias_for, reference_for
from .manifest import (
    Entry,
    Handle,
    Manifest,
    UnmirrorableRootError,
    describe,
)

__all__ = [
    "DEFAULT_FRAMEWORK_REF",
    "Entry",
    "Handle",
    "NARROWING_LIMIT",
    "Manifest",
    "Shape",
    "StubReport",
    "TypeRef",
    "UnmirrorableRootError",
    "alias_for",
    "describe",
    "emit",
    "generate",
    "reference_for",
    # Mounting the command under a downstream framework's own command name, so
    # a framework's users get editor autocomplete from that framework's own CLI.
    "register",
    "render",
    "shape_of",
    "stub_path",
    "verify",
]


#: Past this many identifiers, the per-identifier narrowing stops being the
#: right shape — not by taste, by measurement. Checking one file that imports
#: such a stub goes superlinear in mypy (2.7s at 500 entries, 27.5s at 2,000,
#: past 300s at 10,000), pyright exhausts its runtime's heap at 50,000, and
#: editor completion in pyright reaches 18.8s per keystroke at 10,000 while ty
#: stops offering completions there at all. The threshold sits below the knee
#: rather than at it, because a project grows into the wall between releases.
#:
#: The navigation surface has no such curve — the same 50,000 identifiers check
#: in 1-2s and complete in 0.02s — so the report points there instead of
#: refusing: a project checked only by ty is fine well past this, and a guard
#: that blocked them would enforce a limit they do not have.
NARROWING_LIMIT = 1000


@dataclass(frozen=True)
class StubReport:
    """The outcome of generating or verifying a stub."""

    path: Path
    entries: int
    degraded: int
    #: True when the stored stub already matched; None when not verifying.
    matched: bool | None = None
    #: Why a verification failed, in one line. None when it succeeded.
    reason: str | None = None
    written: bool = False

    @property
    def ok(self) -> bool:
        return self.matched is not False

    @property
    def oversized(self) -> str | None:
        """Why this registry has outgrown the narrowing, or None.

        Reported on the *report* rather than raised or printed, so the core
        stays pure and every surface — the CLI today, anything else later —
        renders one sentence rather than composing its own.
        """
        if self.entries <= NARROWING_LIMIT:
            return None
        return (
            f"{self.entries} identifiers exceeds {NARROWING_LIMIT}, past which "
            "the per-identifier overloads slow or exhaust the type checkers "
            "this project verifies against. The stub was still written; prefer "
            "navigating `framework.objects.<kind>.<namespace>.<name>`, which "
            "stays flat at any size"
        )


def stub_path(root_file: str | Path) -> Path:
    """Where a composition root's stub lives: beside it, same name, ``.pyi``."""
    return Path(root_file).with_suffix(".pyi")


#: Bound on the formatter subprocess. Ruff formats a stub in milliseconds; a
#: minute of silence is a wedged toolchain, and neither generation nor a CI
#: verify may hang on one.
_FORMAT_TIMEOUT = 60.0


def _format(text: str) -> str:
    """Normalize emitted text with the project's formatter, if it is present.

    The emitter already produces formatted output — a test holds it to that —
    so this is a guard against drift rather than a load-bearing step. When ruff
    is absent (or wedged past the timeout) the text passes through unchanged,
    which keeps generation and verification producing identical bytes in the
    same environment either way.
    """
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--stdin-filename",
                "stub.pyi",
                "-",
            ],
            input=text,
            capture_output=True,
            text=True,
            check=False,
            timeout=_FORMAT_TIMEOUT,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return text
    if completed.returncode != 0 or not completed.stdout:
        return text
    return completed.stdout


def render(
    base_dir: Path | str,
    framework_ref: str = DEFAULT_FRAMEWORK_REF,
    strict: bool = False,
) -> tuple[Path, str, Manifest]:
    """Describe the project at `base_dir` and render its stub, writing nothing.

    Returns the path the stub belongs at, its text, and the manifest behind it.
    Generation and verification both route through here, so the two can never
    disagree about what the current stub *should* be.
    """
    base = Path(base_dir)
    with import_state():
        sys.path.insert(0, str(base))
        root, framework = locate_root(framework_ref)
        manifest = describe(framework, base, root)
        root_file = getattr(root, "__file__", None)
        if root_file is None:
            raise UnmirrorableRootError(manifest.root_module, ("<no source file>",))
        return stub_path(root_file), _format(emit(manifest, strict=strict)), manifest


def generate(
    base_dir: Path | str,
    framework_ref: str = DEFAULT_FRAMEWORK_REF,
    strict: bool = False,
) -> StubReport:
    """Write the stub for the project at `base_dir`."""
    path, text, manifest = render(base_dir, framework_ref, strict=strict)
    path.write_text(text, encoding="utf-8", newline="\n")
    return StubReport(
        path=path,
        entries=len(manifest.entries),
        degraded=manifest.degraded,
        written=True,
    )


def verify(
    base_dir: Path | str,
    framework_ref: str = DEFAULT_FRAMEWORK_REF,
    strict: bool = False,
) -> StubReport:
    """Check the stored stub against the project without modifying it.

    A missing stub is a mismatch, not a pass: "no stub" and "current stub" are
    different states, and only one of them is safe to build on.
    """
    path, expected, manifest = render(base_dir, framework_ref, strict=strict)
    report = StubReport(
        path=path, entries=len(manifest.entries), degraded=manifest.degraded
    )
    if not path.exists():
        return replace_reason(
            report, False, f"no stub at {path.name}; run `spoc stubs` to create it"
        )
    # The stored text is normalized through the same formatter before the
    # comparison. Byte-equality of raw texts compared two ruff versions'
    # opinions as much as two stubs: a stub generated under one ruff and
    # verified under another reported "stale" with no content difference at
    # all. Staleness is a claim about content, so both sides are formatted by
    # the ruff doing the verifying — and when ruff is absent, both sides pass
    # through unchanged and the comparison is exactly what it always was.
    stored = _format(path.read_text(encoding="utf-8"))
    if stored == expected:
        return replace_reason(report, True, None)
    return replace_reason(report, False, _first_difference(stored, expected))


def replace_reason(report: StubReport, matched: bool, reason: str | None) -> StubReport:
    """A copy of `report` carrying a verification outcome."""
    return StubReport(
        path=report.path,
        entries=report.entries,
        degraded=report.degraded,
        matched=matched,
        reason=reason,
        written=report.written,
    )


def _first_difference(stored: str, expected: str) -> str:
    """Name the first line that differs, so the mismatch is actionable."""
    stored_lines, expected_lines = stored.splitlines(), expected.splitlines()
    for number, (left, right) in enumerate(
        zip(stored_lines, expected_lines, strict=False), start=1
    ):
        if left != right:
            return f"stub is stale at line {number}: expected {right.strip()!r}"
    if len(expected_lines) > len(stored_lines):
        missing = expected_lines[len(stored_lines)].strip()
        return f"stub is missing {len(expected_lines) - len(stored_lines)} line(s), starting {missing!r}"
    extra = len(stored_lines) - len(expected_lines)
    return f"stub has {extra} line(s) the project no longer declares"
