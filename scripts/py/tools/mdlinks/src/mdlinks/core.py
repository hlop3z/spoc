"""Link extraction and resolution.

Pure functions, no CLI and no I/O beyond reading the files it is handed — the
CLI layer in `cli.py` is a thin adapter over this (Rule 2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Inline Markdown links: [text](target). Reference-style links and bare autolinks
# are out of scope — they are rare in this repo's docs and would need a real
# parser to handle correctly.
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

_SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "data:")

_SKIP_DIRS = {".git", "node_modules", "target", "dist", "build", ".venv", "__pycache__"}


@dataclass(frozen=True)
class BrokenLink:
    """A relative link whose target does not exist on disk."""

    source: Path
    target: str
    line: int

    def __str__(self) -> str:
        return f"{self.source}:{self.line}: {self.target}"


def extract_links(text: str) -> list[tuple[str, int]]:
    """Return every inline link target in `text` with its 1-indexed line number."""
    found: list[tuple[str, int]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _LINK.finditer(line):
            found.append((match.group(1), lineno))
    return found


def is_local(target: str) -> bool:
    """True when the target is a relative path this tool can resolve."""
    if not target or target.startswith(_SKIP_PREFIXES):
        return False
    return not target.startswith("/")


def check_file(path: Path) -> list[BrokenLink]:
    """Report every local link in one Markdown file that does not resolve."""
    broken: list[BrokenLink] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    for target, lineno in extract_links(text):
        if not is_local(target):
            continue
        # Strip an anchor: docs/x.md#section resolves against docs/x.md.
        bare = target.split("#", 1)[0]
        if not bare:
            continue
        if not (path.parent / bare).resolve().exists():
            broken.append(BrokenLink(source=path, target=target, line=lineno))

    return broken


def markdown_files(root: Path) -> list[Path]:
    """Every Markdown file under `root`, skipping vendored and build directories."""
    if root.is_file():
        return [root]
    return sorted(
        p for p in root.rglob("*.md") if not any(part in _SKIP_DIRS for part in p.parts)
    )


def check_paths(roots: list[Path]) -> list[BrokenLink]:
    """Check every Markdown file under each root."""
    broken: list[BrokenLink] = []
    for root in roots:
        for path in markdown_files(root):
            broken.extend(check_file(path))
    return broken
