"""Thin CLI adapter over `mdlinks.core` (Rule 2 — no logic lives here)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from mdlinks.core import check_paths

app = cyclopts.App(
    name="mdlinks",
    help="Find broken relative links in Markdown files.",
)


@app.default
def main(
    paths: Annotated[
        list[Path] | None,
        cyclopts.Parameter(
            help="Files or directories to check. Defaults to the current directory."
        ),
    ] = None,
    *,
    as_json: Annotated[
        bool,
        cyclopts.Parameter(
            name=["--json"], help="Emit JSON instead of a human-readable list."
        ),
    ] = False,
) -> int:
    """Report every relative Markdown link whose target does not exist.

    Exits non-zero when any broken link is found, so it can gate a check run.
    """
    roots = paths or [Path(".")]
    broken = check_paths(roots)

    if as_json:
        json.dump(
            [
                {"source": str(b.source), "target": b.target, "line": b.line}
                for b in broken
            ],
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    elif broken:
        for item in broken:
            print(item)
        print(f"\n{len(broken)} broken link(s)", file=sys.stderr)
    else:
        print("no broken links")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(app())
