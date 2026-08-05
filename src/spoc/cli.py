"""
The composed ``spoc`` program.

One parser; each surface registers its own subcommands (`spoc.scaffold.cli`
mounts ``init``, `spoc.diagnostics.cli` mounts ``check``/``list``/``explain``)
and attaches a handler. This module only parses, dispatches, and maps the
library's refusals to exit codes — a SPOC or scaffold refusal is a clean
one-line error, while an exception raised by an app's own module code
propagates untouched (that error is the app author's, traceback and all).

The kernel never imports this module; it is entry-point metadata until the
console script runs.
"""

import argparse
import sys

from .core.exceptions import SpocError
from .diagnostics import cli as diagnostics_cli
from .diagnostics.locate import LocateError
from .scaffold import cli as scaffold_cli

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spoc",
        description=(
            "Scaffold, validate, and inspect spoc projects: init generates a "
            "runnable project; check dry-boots and reports problems before "
            "runtime; list and explain read the registry."
        ),
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    scaffold_cli.register(subcommands)
    diagnostics_cli.register(subcommands)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code rather than raising."""
    args = _build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    # SpocError covers the scaffolder's refusals, the kernel's identity and
    # configuration errors, and the diagnostics' resolution failures alike;
    # LocateError is the diagnostics' own "framework not found"; ValueError
    # covers argument-shape refusals from the operations layer.
    except (SpocError, LocateError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
