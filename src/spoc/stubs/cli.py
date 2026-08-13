"""
The ``spoc stubs`` subcommand — a thin adapter by contract.

Parses argv, calls one operation, renders lines, returns an exit code. Which
stub is correct, where it belongs, and whether the stored one is current are all
decided in :mod:`spoc.stubs`; nothing here knows how a stub is built.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..locate import DEFAULT_FRAMEWORK_REF

__all__ = ["register"]


def _degraded_note(degraded: int, entries: int) -> str:
    if not degraded:
        return ""
    return (
        f" ({degraded} of {entries} could not be typed faithfully and fall back to Any)"
    )


def _run_stubs(args: argparse.Namespace) -> int:
    # Imported when a command runs rather than when one is mounted. These
    # operations are defined in this package's __init__, which now publishes
    # `register`, so importing them at module scope would have the surface
    # import its own adapter while still initializing. Deferring also keeps the
    # mount free of work: mounting describes commands, it does not load the
    # machinery behind them.
    from . import generate, verify

    if args.check:
        report = verify(args.path, args.framework, strict=args.strict)
        if report.ok:
            print(
                f"OK: {report.path.name} is current "
                f"({report.entries} identifiers)"
                f"{_degraded_note(report.degraded, report.entries)}"
            )
            return 0
        print(f"stubs: {report.reason}", file=sys.stderr)
        return 1

    report = generate(args.path, args.framework, strict=args.strict)
    print(
        f"wrote {report.path} ({report.entries} identifiers)"
        f"{_degraded_note(report.degraded, report.entries)}"
    )
    # A note, not a failure: the stub is written and usable, and the exit code
    # stays 0 so a build that generates stubs does not start failing on a
    # project that merely grew.
    if report.oversized:
        print(f"stubs: {report.oversized}", file=sys.stderr)
    return 0


def register(subcommands: argparse._SubParsersAction) -> None:
    """Mount ``stubs`` on a parser you own.

    Lets a framework built on SPOC give its own users editor autocomplete under
    its own command name. The shipped ``spoc`` program mounts this command the
    same way.

    Provisional: may change incompatibly in a minor release. What is promised is
    which commands the mount contributes and what invoking them does; the type of
    ``subcommands`` is ``argparse``'s and not SPOC's, so promising it would commit
    every downstream framework to ``argparse`` too. It settles when a framework
    outside this package has actually mounted it, or when SPOC commits to its
    parser choice and the mount can take a type it owns.
    """
    parser = subcommands.add_parser(
        "stubs",
        help="Generate a type stub for the project's resolution surface.",
        description=(
            "Dry-boot the project and write a type stub beside its composition "
            "root, so resolve() returns the real type of each component and "
            "editors complete both the identifier and the object. The stub "
            "never executes, so it adds no runtime coupling between apps. "
            "Note: generating imports your app modules."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory).",
    )
    parser.add_argument(
        "--framework",
        default=DEFAULT_FRAMEWORK_REF,
        help=(
            "module.path:attribute holding the Framework "
            f"(default: {DEFAULT_FRAMEWORK_REF}, what `spoc init` emits)."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the stored stub is current without writing it.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Omit the catch-all overload, making a misspelled identifier a "
            "type error. Requires every resolve() call to use a literal."
        ),
    )
    parser.set_defaults(handler=_run_stubs)
