"""
The diagnostics subcommands — thin adapters by contract.

Each handler parses nothing but argv, calls the one operation, and renders
the result as plain lines. All logic — location, booting, filtering,
precision of failure — lives in :mod:`spoc.diagnostics.core` and the kernel.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..locate import DEFAULT_FRAMEWORK_REF
from ..projection import FORMAT_VERSION
from .core import check, explain, list_records

__all__ = ["register"]


def _add_common(parser: argparse.ArgumentParser) -> None:
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
        "--json",
        dest="as_json",
        action="store_true",
        help=(
            "Emit the result as JSON on stdout and nothing else. This output "
            "is the covered surface; the prose rendering is free to change."
        ),
    )


def _emit(document: dict[str, Any]) -> None:
    """One JSON document on stdout, nothing on stderr.

    ``ensure_ascii`` for the same reason the projection document escapes: this
    is piped onward through consoles whose encoding nobody chose. Prose and
    document never interleave — a consumer parses the whole of stdout.
    """
    print(json.dumps(document, indent=2, ensure_ascii=True))


def _run_check(args: argparse.Namespace) -> int:
    report = check(args.path, args.framework)
    if args.as_json:
        _emit(report.to_dict())
        return 0 if report.ok else 1
    for finding in report.findings:
        print(f"{finding.area}: {finding.message}", file=sys.stderr)
    if report.ok:
        print(f"OK: {args.path} checks out clean")
        return 0
    count = len(report.findings)
    print(f"{count} problem{'s' if count != 1 else ''} found", file=sys.stderr)
    return 1


def _run_list(args: argparse.Namespace) -> int:
    records = list_records(
        args.path, args.framework, kind=args.kind, namespace=args.namespace
    )
    if args.as_json:
        # Each entry is the projection document's component object, so the
        # wrapper carries the projection's own format version — the payload's
        # shape IS that entry, and its version travels with it. Not the full
        # projection document: a narrowed listing of a *started* project must
        # not claim the document's "every declared kind" key.
        _emit(
            {
                "format_version": FORMAT_VERSION,
                "components": [asdict(record) for record in records],
            }
        )
        return 0
    for record in records:
        print(record.identifier)
    return 0


def _run_explain(args: argparse.Namespace) -> int:
    record = explain(args.identifier, args.path, args.framework)
    if args.as_json:
        _emit(
            {
                "format_version": FORMAT_VERSION,
                "component": asdict(record),
            }
        )
        return 0
    print(f"identifier:  {record.identifier}")
    print(f"kind:        {record.kind}")
    print(f"namespace:   {record.namespace}")
    print(f"object_name: {record.object_name}")
    print(f"object:      {record.location}")
    print(f"shape:       {record.shape}")
    return 0


def register(subcommands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Mount ``check``/``list``/``explain`` on a parser you own.

    The inspection half of what a framework built on SPOC publishes under its own
    command name. A downstream CLI that can generate a project but not validate
    one is half a CLI, which is why this mount carries the same tier as the
    generation line. The shipped ``spoc`` program mounts these commands the same
    way.

    Provisional: may change incompatibly in a minor release. What is promised is
    which commands the mount contributes and what invoking them does; the type of
    ``subcommands`` is ``argparse``'s and not SPOC's, so promising it would commit
    every downstream framework to ``argparse`` too. It settles when a framework
    outside this package has actually mounted it, or when SPOC commits to its
    parser choice and the mount can take a type it owns.
    """
    check_parser = subcommands.add_parser(
        "check",
        help="Validate the project before runtime.",
        description=(
            "Dry-boot the project and report configuration problems, "
            "unresolvable apps and plugins, dependency cycles, identity "
            "collisions, and coroutine hooks the synchronous lifecycle would "
            "refuse. Note: checking imports your app modules."
        ),
    )
    _add_common(check_parser)
    check_parser.set_defaults(handler=_run_check)

    list_parser = subcommands.add_parser(
        "list",
        help="List every registered identifier.",
        description="Boot, enumerate the registry, tear down.",
    )
    _add_common(list_parser)
    list_parser.add_argument("--kind", default=None, help="Narrow to one kind.")
    list_parser.add_argument(
        "--namespace", default=None, help="Narrow to one namespace."
    )
    list_parser.set_defaults(handler=_run_list)

    explain_parser = subcommands.add_parser(
        "explain",
        help="Describe one registered identifier.",
        description="Resolve kind:namespace.object_name and describe the record.",
    )
    explain_parser.add_argument("identifier", help="kind:namespace.object_name")
    _add_common(explain_parser)
    explain_parser.set_defaults(handler=_run_explain)
