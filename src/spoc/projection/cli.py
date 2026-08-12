"""
The ``spoc projection`` subcommand — a thin adapter by contract.

Parses argv, calls one operation, writes the document, returns an exit code.
What the document contains, how it is ordered, and what boot depth produces it
are all decided in :mod:`spoc.projection`; nothing here knows.

Standard output carries the document and nothing else, so the command pipes
into a validator or a generator without a flag to suppress chatter. Failures
are the kernel's own and reach the error stream through the composed parser's
one handler, which is why there is no ``try`` in this module.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..locate import DEFAULT_FRAMEWORK_REF
from . import dumps, project

__all__ = ["register"]


def _run_projection(args: argparse.Namespace) -> int:
    sys.stdout.write(dumps(project(args.path, args.framework)))
    return 0


def register(subcommands: argparse._SubParsersAction) -> None:
    """Mount ``projection`` on the composed ``spoc`` parser."""
    parser = subcommands.add_parser(
        "projection",
        help="Write the registry as a JSON document.",
        description=(
            "Dry-boot the project and write its registry to standard output as "
            "JSON: every registered component, its canonical identifier and the "
            "three facets composing it, where its object is defined, and its "
            "shape, plus the declared kind set. Validates against the schema "
            "published with spoc. Discovery runs but initialization does not, "
            "so a project whose startup hooks would fail is still describable. "
            "Note: projecting imports your app modules."
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
    parser.set_defaults(handler=_run_projection)
