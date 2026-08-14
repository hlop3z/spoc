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

# From the modules that define these, not from this package's __init__: the
# package publishes `register`, so importing back through __init__ would make
# the surface depend on its own adapter mid-initialization.
from .document import dumps
from .produce import project

__all__ = ["register"]


def _run_projection(args: argparse.Namespace) -> int:
    sys.stdout.write(dumps(project(args.path, args.framework)))
    return 0


def register(subcommands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Mount ``projection`` on a parser you own.

    Lets a framework built on SPOC hand its own users the registry as data under
    its own command name. The shipped ``spoc`` program mounts this command the
    same way.

    Provisional: may change incompatibly in a minor release. What is promised is
    which commands the mount contributes and what invoking them does; the type of
    ``subcommands`` is ``argparse``'s and not SPOC's, so promising it would commit
    every downstream framework to ``argparse`` too. It settles when a framework
    outside this package has actually mounted it, or when SPOC commits to its
    parser choice and the mount can take a type it owns. The *document* the
    command writes is promised separately and more strongly — see
    ``schema:projection/document``.
    """
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
