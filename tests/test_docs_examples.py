"""Every Python fence under ``docs/docs/`` runs, or says why it doesn't.

The docs snippet policy (docs-dx, `documentation-integrity` spec) — every
Python fence is in exactly one state, and silence is not one of them:

1. **Standalone** (no ``title=``): executed as its own module; printed output
   must be mirrored in ``#> `` comments (regenerate with
   ``uv run pytest tests/test_docs_examples.py --update-examples``).
2. **Project file** (``title="path"``): written verbatim into a per-page tree,
   any language, in page order (a later fence with the same title overwrites —
   the page evolves the file). A page declaring Python project files must also
   declare its ``title="main.py"`` entry, which runs as a subprocess exactly
   the way a reader would run it.
3. **Marked** (``test="skip"`` in the fence line): counted, reported, and held
   under ``SKIP_CEILING`` — for output-only and deliberately-partial blocks,
   never for rot. Run with ``-rs`` to list them.

pytest-examples 0.0.18 facts, verified against the installed source
(docs-dx task 1.1):

- ``find_examples`` collects only fences whose info string starts with ``py``;
  other languages are invisible to it, which is why tree assembly scans fences
  itself (``_FENCE``) — that scan is page-to-files placement, not parsing of
  any standard format.
- Fence-info settings (``title="…"``, ``test="skip"``) come from
  ``CodeExample.prefix_settings()``. The tool ships no skip semantic of its
  own — honoring ``test="skip"`` is the consuming suite's job (pydantic's own
  docs use the same convention).
- ``run_print_check`` fails when a snippet's prints are not mirrored by
  ``#> `` comments, so output display is enforced, not optional;
  ``run_print_update`` under ``--update-examples`` regenerates them.
- Examples share no state: each runs as a fresh module. Pages that need
  accumulation declare project files (state 2) instead of relying on
  fence-to-fence memory.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_examples import CodeExample, EvalExample, find_examples

DOCS_DIR = Path(__file__).parent.parent / "docs" / "docs"

# A reasoned ceiling, not an escape hatch: raising it is a visible diff the
# review must justify (design D2). Starts at zero — every current fence either
# runs or gets completed until it does.
SKIP_CEILING = 0

# Entry-file convention for state 2: the fence a reader would run.
ENTRY_TITLE = "main.py"

_FENCE = re.compile(
    r"^(?P<indent>[ \t]*)```(?P<info>[^\n]*)\n(?P<body>.*?)\n(?P=indent)```",
    re.MULTILINE | re.DOTALL,
)
_SETTING = re.compile(r"""([^{\s]+?)=(['"])(.+?)\2""")


def _settings(info: str) -> dict[str, str]:
    return {m.group(1): m.group(3) for m in _SETTING.finditer(info)}


def _title(example: CodeExample) -> str | None:
    return example.prefix_settings().get("title")


def _is_skip(example: CodeExample) -> bool:
    return example.prefix_settings().get("test") == "skip"


ALL_EXAMPLES = list(find_examples(str(DOCS_DIR)))
STANDALONE = [ex for ex in ALL_EXAMPLES if _title(ex) is None]
TREE_PAGES = sorted(
    {ex.path for ex in ALL_EXAMPLES if _title(ex) is not None and not _is_skip(ex)}
)


def _page_files(page: Path) -> list[tuple[str, str]]:
    """Titled fences of any language, verbatim, in page order."""
    files = []
    for m in _FENCE.finditer(page.read_text("utf-8")):
        settings = _settings(m.group("info"))
        title = settings.get("title")
        if title is None or settings.get("test") == "skip":
            continue
        indent = m.group("indent")
        body = m.group("body")
        if indent:
            body = re.sub(rf"^{indent}", "", body, flags=re.MULTILINE)
        files.append((title, body + "\n"))
    return files


@pytest.fixture(autouse=True)
def _utf8_example_files(monkeypatch: pytest.MonkeyPatch):
    """Write example files as UTF-8 regardless of platform.

    pytest-examples 0.0.18 reads markdown as UTF-8 but writes the extracted
    module with the locale default, so on Windows any non-ASCII character in a
    snippet becomes a SyntaxError before the example even runs. Upstream
    defect in ``EvalExample._write_file``; remove when fixed.
    """

    def _write_file(self: EvalExample, example: CodeExample) -> Path:
        python_file = self.tmp_path / f"{example.module_name}.py"
        python_file.write_text(example.source, encoding="utf-8")
        return python_file

    monkeypatch.setattr(EvalExample, "_write_file", _write_file)


def test_examples_are_collected():
    """A path or glob regression must not turn this suite vacuous."""
    assert ALL_EXAMPLES, f"no Python fences found under {DOCS_DIR}"


@pytest.mark.parametrize("example", STANDALONE, ids=str)
def test_standalone_snippet(example: CodeExample, eval_example: EvalExample):
    if _is_skip(example):
        pytest.skip(f'marked test="skip": {example}')
    if eval_example.update_examples:
        eval_example.run_print_update(example)
    else:
        eval_example.run_print_check(example)


@pytest.mark.parametrize(
    "page", TREE_PAGES, ids=lambda p: str(p.relative_to(DOCS_DIR)).replace("\\", "/")
)
def test_page_project(page: Path, tmp_path: Path):
    files = _page_files(page)
    titles = [title for title, _ in files]
    assert ENTRY_TITLE in titles, (
        f"{page.name} declares project files {titles} but no "
        f'title="{ENTRY_TITLE}" entry — a project page must say how it runs'
    )
    for title, body in files:
        dest = tmp_path.joinpath(*title.split("/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, ENTRY_TITLE],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, (
        f"{page.name}'s project failed to run:\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )


def test_skip_ledger():
    """State 3 stays visible and bounded — silence is not an allowed state."""
    skipped = [str(ex) for ex in ALL_EXAMPLES if _is_skip(ex)]
    assert len(skipped) <= SKIP_CEILING, (
        f"{len(skipped)} fences marked test=\"skip\" exceeds the ceiling of "
        f"{SKIP_CEILING}:\n" + "\n".join(skipped) + "\n"
        "Complete them into runnable state, or raise SKIP_CEILING in the same "
        "diff with the justification in review."
    )
