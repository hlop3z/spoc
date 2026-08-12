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
from pathlib import Path

from .core.exceptions import SpocError
from .diagnostics import cli as diagnostics_cli
from .locate import LocateError, locate_framework
from .scaffold import cli as scaffold_cli
from .scaffold.cache import DirectoryCache
from .scaffold.remote import HttpFetcher, HttpRevisionResolver
from .scaffold.sources import InstalledTemplateSources, RemoteTemplateSource
from .testing import import_state

__all__ = ["main"]


def _template_sources() -> InstalledTemplateSources:
    """Every template source the shipped CLI can resolve, wired together.

    The retrieval adapters are constructed here and nowhere else. That keeps the
    kernel's one outbound network path visible in a single place, and keeps the
    scaffold's own CLI free of any knowledge that remote references exist — it
    passes a reference through and the resolver decides what it designates.
    """
    return InstalledTemplateSources(
        RemoteTemplateSource(
            revisions=HttpRevisionResolver(),
            fetcher=HttpFetcher(),
            cache=DirectoryCache(),
        )
    )


def _derive_kinds(project_root: Path) -> tuple[str, ...]:
    """Kinds from the project's own declaration — `spoc app` never makes the
    author restate what framework.py already states. Wired here because only
    the composition root may join the scaffold and diagnostics surfaces."""
    try:
        with import_state():
            sys.path.insert(0, str(project_root))
            return locate_framework().kinds
    except LocateError as exc:
        raise ValueError(
            f"Could not derive the kinds: {exc} — or state them explicitly "
            "with --kinds models,views"
        ) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spoc",
        description=(
            "Scaffold, validate, and inspect spoc projects: init generates a "
            "runnable project, app adds one to it; check dry-boots and reports "
            "problems before runtime; list and explain read the registry."
        ),
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    scaffold_cli.register(
        subcommands, derive_kinds=_derive_kinds, source_factory=_template_sources
    )
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
