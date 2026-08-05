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
from collections.abc import Callable
from pathlib import Path

from .operations import DEFAULT_APP_NAME, DEFAULT_KINDS, add_app, init_project
from .sink import DirectorySink
from .sources import BUILTIN_SET, InstalledTemplateSources

__all__ = ["register"]

#: How the composition root supplies kind derivation: project root → kinds.
DeriveKinds = Callable[[Path], tuple[str, ...]]


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


def _run_app(args: argparse.Namespace, derive_kinds: DeriveKinds | None) -> int:
    if args.kinds is not None:
        kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    elif derive_kinds is not None:
        kinds = derive_kinds(args.path)
    else:
        raise ValueError(
            "State the kinds with --kinds models,views, or run inside a "
            "project whose framework declaration is locatable"
        )

    added = add_app(
        source=InstalledTemplateSources(),
        sink_factory=lambda app_dir: DirectorySink(args.path / app_dir),
        app_name=args.name,
        kinds=kinds,
        template_set=args.template,
    )

    print(f"Created {args.path / added.app_dir}")
    for planned in added.plan:
        print(f"  {added.app_dir}/{planned.path}")
    print(
        f'\nInstall it: add "{added.config_reference}" to a mode list under '
        f"[spoc.apps] in config/spoc.toml, e.g.\n"
        f'  development = [..., "{added.config_reference}"]'
    )
    return 0


def register(
    subcommands: argparse._SubParsersAction,
    derive_kinds: DeriveKinds | None = None,
) -> None:
    """Mount ``init`` and ``app`` on the composed ``spoc`` parser.

    ``derive_kinds`` is injected by the composition root — the scaffold never
    imports the surface that can locate a framework declaration.
    """
    init = subcommands.add_parser(
        "init",
        help="Generate a new project that starts unedited.",
        description=(
            "Generate a new project: configuration, framework declaration, one "
            "app, and an entry point. Add further apps with `spoc app <name>` — "
            "a spoc app is an __init__ plus a module per kind."
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
        help=(
            f"Template set to render (default: {BUILTIN_SET}). An installed "
            "set's name, or a directory path (contains a separator, e.g. "
            "./mytemplates)."
        ),
    )
    init.set_defaults(handler=_run_init)

    app = subcommands.add_parser(
        "app",
        help="Generate one additional app into an existing project.",
        description=(
            "Generate an app — one module per kind, each holding a declared "
            "component, the same shape init emits. Kinds are derived from the "
            "project's framework declaration unless stated with --kinds. The "
            "configuration is never edited; the exact entry to add is printed."
        ),
    )
    app.add_argument("name", help="App name (lowercase, snake_case).")
    app.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Project root (default: current directory).",
    )
    app.add_argument(
        "--kinds",
        default=None,
        help="Comma-separated kinds (default: derived from the declaration).",
    )
    app.add_argument(
        "--template",
        default=BUILTIN_SET,
        help=f"Template set whose app shape to render (default: {BUILTIN_SET}).",
    )
    app.set_defaults(handler=lambda args: _run_app(args, derive_kinds))
