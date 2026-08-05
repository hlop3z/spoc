"""
The scaffold's command-line adapter — the ``init`` subcommand.

Thin by contract: it parses arguments, wires the concrete adapters, calls the
operation, and renders the result. It holds no generation logic, no conflict
rules, and no template knowledge — everything it does is available to a caller
who never touches argv. The composed ``spoc`` program (``spoc.cli``) mounts it
via :func:`register`.

``argparse`` is the standard library, which is why the scaffolder can ship
inside a package whose published dependency set is empty.
"""

import argparse
from pathlib import Path

from .operations import DEFAULT_APP_NAME, DEFAULT_KINDS, init_project
from .sink import DirectorySink
from .sources import BUILTIN_SET, InstalledTemplateSources

__all__ = ["register"]


def _run_init(args: argparse.Namespace) -> int:
    destination = args.path if args.path is not None else Path.cwd() / args.name
    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())

    plan = init_project(
        source=InstalledTemplateSources(),
        sink=DirectorySink(destination),
        project_name=args.name,
        app_name=args.app,
        kinds=kinds,
        template_set=args.template,
    )

    print(f"Created {destination}")
    for planned in plan:
        print(f"  {planned.path}")
    print(f"\nNext:\n  cd {destination}\n  python main.py")
    return 0


def register(subcommands: argparse._SubParsersAction) -> None:
    """Mount ``init`` on the composed ``spoc`` parser."""
    init = subcommands.add_parser(
        "init",
        help="Generate a new project that starts unedited.",
        description=(
            "Generate a new project: configuration, framework declaration, one "
            "app, and an entry point. Add further apps by copying the generated "
            "one — a spoc app is an __init__ plus a module per kind."
        ),
    )
    init.add_argument("name", help="Project name (lowercase, snake_case).")
    init.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Directory to generate into. Defaults to ./<name>.",
    )
    init.add_argument(
        "--app",
        default=DEFAULT_APP_NAME,
        help=f"Name of the starter app (default: {DEFAULT_APP_NAME}).",
    )
    init.add_argument(
        "--kinds",
        default=",".join(DEFAULT_KINDS),
        help=(
            "Comma-separated kinds the framework declares "
            f"(default: {','.join(DEFAULT_KINDS)})."
        ),
    )
    init.add_argument(
        "--template",
        default=BUILTIN_SET,
        help=f"Template set to render (default: {BUILTIN_SET}).",
    )
    init.set_defaults(handler=_run_init)
