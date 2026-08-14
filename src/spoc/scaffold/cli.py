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

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from .operations import DEFAULT_APP_NAME, DEFAULT_KINDS, add_app, init_project
from .plan import TemplateSource
from .provenance import read_origin
from .sink import DirectorySink
from .sources import BUILTIN_SET, InstalledTemplateSources

__all__ = ["register"]

#: How the composition root supplies kind derivation: project root → kinds.
DeriveKinds = Callable[[Path], tuple[str, ...]]

#: How the composition root supplies template resolution. Defaulted so a caller
#: mounting this surface without wiring retrieval still gets local template sets.
SourceFactory = Callable[[], TemplateSource]


def _run_init(args: argparse.Namespace, sources: SourceFactory) -> int:
    destination = args.path if args.path is not None else Path.cwd() / args.name
    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())

    plan = init_project(
        source=sources(),
        sink=DirectorySink(destination),
        project_name=args.name,
        app_name=args.app,
        kinds=kinds,
        template_set=args.template,
    )

    print(f"Created {destination}")
    for planned in plan:
        print(f"  {planned.path}")

    # Read back from the record rather than from the resolution, so what is
    # reported is exactly what the project will claim about itself later.
    origin = read_origin(destination)
    if origin is not None and origin.revision:
        print(
            f"\nGenerated from {origin.reference} at revision {origin.revision}.\n"
            f"Reproduce this exact project with:\n"
            f"  --template {_pinned(origin.reference, origin.revision)}"
        )

    print(f"\nNext:\n  cd {destination}\n  python main.py")
    return 0


def _pinned(reference: str, revision: str) -> str:
    """The same reference, pinned to the revision it resolved to.

    Stated so a moving reference can be turned into a reproducible one by
    copying a line, rather than by the author working out the syntax.
    """
    base, _, _ = reference.partition("#")
    base = base.rpartition("@")[0] if "@" in base.rpartition("/")[2] else base
    fragment = reference.partition("#")[2]
    pinned = f"{base}@{revision}"
    return f"{pinned}#{fragment}" if fragment else pinned


def _run_app(
    args: argparse.Namespace,
    derive_kinds: DeriveKinds | None,
    sources: SourceFactory,
) -> int:
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
        source=sources(),
        sink_factory=lambda app_dir: DirectorySink(args.path / app_dir),
        app_name=args.name,
        kinds=kinds,
        template_set=args.template,
        read_origin=lambda: read_origin(args.path),
    )

    if added.divergence:
        print(f"note: {added.divergence}\n")
    print(f"Created {args.path / added.app_dir}")
    for planned in added.plan:
        print(f"  {added.app_dir}/{planned.path}")
    print(
        f'\nInstall it: add "{added.config_reference}" to a mode list under '
        f"[spoc.apps] in config/spoc.toml, e.g.\n"
        f'  development = [..., "{added.config_reference}"]'
    )
    return 0


#: Stated in `--template` help on both subcommands. One definition, because a
#: help text that lists different forms than the parser accepts is a defect.
_TEMPLATE_HELP = (
    "Template set to render (default: {default}). One of: an installed set's "
    "name; a directory path (./mytemplates, C:\\templates); gh:owner/repo"
    "[@revision][#subdirectory=path]; an https:// archive URL; or "
    "git+https://host/owner/repo[@revision]. A remote reference is the only "
    "thing that causes spoc to access the network."
)


def register(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
    derive_kinds: DeriveKinds | None = None,
    source_factory: SourceFactory | None = None,
) -> None:
    """Mount ``init`` and ``app`` on a parser you own.

    This is how a framework built on SPOC publishes the generation line under
    its own command name — ``hello init`` rather than a second program the
    author's users have to know about. The shipped ``spoc`` program mounts these
    commands the same way, so there is no privileged assembly path this one
    cannot reach.

    ``derive_kinds`` and ``source_factory`` are injected by the composition root
    — the scaffold never imports the surface that can locate a framework
    declaration, and never decides for itself which sources exist. Without a
    factory it resolves local template sets only, so mounting this surface never
    silently acquires a network path.

    Provisional: may change incompatibly in a minor release. What is promised is
    which commands the mount contributes and what invoking them does; the type of
    ``subcommands`` is ``argparse``'s and not SPOC's, so promising it would commit
    every downstream framework to ``argparse`` too. It settles when a framework
    outside this package has actually mounted it — at which point the shape is
    fixed against a real second caller rather than a guess — or when SPOC commits
    to its parser choice and the mount can take a type it owns.
    """
    sources: SourceFactory = source_factory or InstalledTemplateSources
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
        help=_TEMPLATE_HELP.format(default=BUILTIN_SET),
    )
    init.set_defaults(handler=lambda args: _run_init(args, sources))

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
        help=_TEMPLATE_HELP.format(default=BUILTIN_SET),
    )
    app.set_defaults(handler=lambda args: _run_app(args, derive_kinds, sources))
