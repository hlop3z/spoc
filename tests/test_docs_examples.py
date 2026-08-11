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
  CAUTION: run it as ``PYTHONUTF8=1 uv run pytest … --update-examples``.
  ``_modify_files`` reads and writes the page with the interpreter's locale
  encoding while ``find_examples`` reads it as UTF-8, so wherever the two
  codecs disagree on a character count the rewrite is spliced at the wrong
  offset and the page is corrupted around the fence — on cp1252 a single em
  dash anywhere above the fence is enough, and these pages are full of them.
  Line endings are not involved: an LF checkout corrupts identically, and
  UTF-8 mode leaves CRLF intact. Verified both ways against 0.0.18.
- Examples share no state: each runs as a fresh module. Pages that need
  accumulation declare project files (state 2) instead of relying on
  fence-to-fence memory.
- Both locale-encoding defects above are already fixed upstream — pydantic/
  pytest-examples#66, merged 2026-07-13, after 0.0.18 shipped. Nothing to
  report and nothing to contribute; when a release carrying it lands, raise the
  pin and delete the ``_utf8_example_files`` fixture and the caution with it.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_examples import CodeExample, EvalExample, find_examples

DOCS_DIR = Path(__file__).parent.parent / "docs" / "docs"

# A reasoned ceiling, not an escape hatch: raising it is a visible diff the
# review must justify (design D2). The six: two lifecycle call-shape
# fragments (start one-liner, await pair), framework.md's boot-shape fragment,
# vocabulary.md's hook-dispatch loop, stability.md's source quotation, and
# apps.md's build-time-included storefront file.
SKIP_CEILING = 6

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


# The tutorial's entry serves HTTP forever, so the generic run-main.py test
# would hang on it; test_framework_tutorial drives it end-to-end instead.
TUTORIAL_PAGE = DOCS_DIR / "learn" / "build-a-framework.md"

ALL_EXAMPLES = list(find_examples(str(DOCS_DIR)))
STANDALONE = [ex for ex in ALL_EXAMPLES if _title(ex) is None]
TREE_PAGES = sorted(
    {ex.path for ex in ALL_EXAMPLES if _title(ex) is not None and not _is_skip(ex)}
    - {TUTORIAL_PAGE}
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
    snippet becomes a SyntaxError before the example even runs. Upstream defect
    in ``EvalExample._write_file``, fixed by pytest-examples#66 and unreleased;
    remove this fixture when a release carrying it is pinned. It stays even
    though ``PYTHONUTF8=1`` would also cure it — a plain ``uv run pytest`` must
    pass without the caller knowing to set anything.
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
    _write_page_tree(page, tmp_path)
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


def _write_page_tree(page: Path, dest: Path) -> None:
    for title, body in _page_files(page):
        target = dest.joinpath(*title.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


def test_framework_tutorial(tmp_path: Path):
    """The Build a Framework page, end to end (`framework-tutorial` spec).

    Assemble the page's files in page order, boot the framework the reader
    built, serve HTTP on an ephemeral port (argv `0` — the page's own port
    argument), and assert the exact responses the page displays. Single
    request per route, no sleeps: the server prints its bound port before
    serving, so the test reads that line instead of polling.
    """
    import json
    import urllib.request

    _write_page_tree(TUTORIAL_PAGE, tmp_path)
    proc = subprocess.Popen(
        [sys.executable, "main.py", "0"],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline().strip()
        if not line.startswith("Serving on"):
            _, stderr = proc.communicate(timeout=30)
            pytest.fail(f"tutorial project failed to boot:\n{line}\n{stderr}")
        port = int(line.rsplit(":", 1)[1])

        def get(path: str) -> object:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}{path}", timeout=30
            ) as response:
                return json.load(response)

        # The exact payloads the page's curl blocks display.
        assert get("/hello/greet") == {"message": "Hello from a framework you built"}
        assert get("/hello/goodbye") == {"message": "That's the whole trick"}
    finally:
        proc.kill()


@pytest.mark.parametrize(
    "page_path", ["index.md", "getting-started/starter.md"], ids=lambda p: p
)
def test_displayed_starter_help_is_real(page_path: str, tmp_path: Path):
    """The `--help` output the docs display is the generated starter's, verbatim.

    Generates the real starter (builtin set, offline), runs its entry point,
    and compares against the page's displayed block — the landing payoff
    cannot go stale (design D5).
    """
    import os

    page = (DOCS_DIR / Path(*page_path.split("/"))).read_text("utf-8")
    match = re.search(r"^usage: myproject.*?(?=\n```)", page, re.MULTILINE | re.DOTALL)
    assert match, f"{page_path} lost its starter --help block"
    displayed = match.group(0)

    init = subprocess.run(
        [
            sys.executable,
            "-m",
            "spoc.cli",
            "init",
            "myproject",
            "--template",
            "starter",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert init.returncode == 0, f"spoc init failed:\n{init.stdout}\n{init.stderr}"
    shown = subprocess.run(
        [sys.executable, "main.py", "--help"],
        cwd=tmp_path / "myproject",
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={**os.environ, "COLUMNS": "80"},
    )
    assert shown.returncode == 0, shown.stderr

    def normalize(text: str) -> list[str]:
        return [line.rstrip() for line in text.strip().splitlines() if line.strip()]

    assert normalize(displayed) == normalize(shown.stdout), (
        f"{page_path} displays stale starter --help output — "
        "update the block to what the generated project actually prints"
    )


def test_error_index_is_complete():
    """Every exception `spoc` exports has a row in the error index.

    The index page is authored prose; only completeness is mechanical. A new
    public exception type cannot ship without documenting what triggers it
    (`documentation-integrity` spec).
    """
    import spoc

    page = (DOCS_DIR / "api" / "errors.md").read_text("utf-8")
    exported_exceptions = [
        name
        for name in spoc.__all__
        if isinstance(obj := getattr(spoc, name), type)
        and issubclass(obj, BaseException)
    ]
    assert exported_exceptions, "spoc exports no exception types — extraction bug?"
    missing = [name for name in exported_exceptions if f"`{name}`" not in page]
    assert not missing, (
        f"exceptions missing from docs/docs/api/errors.md: {missing} — "
        "add a trigger-and-fix row for each"
    )


def test_skip_ledger():
    """State 3 stays visible and bounded — silence is not an allowed state."""
    skipped = [str(ex) for ex in ALL_EXAMPLES if _is_skip(ex)]
    assert len(skipped) <= SKIP_CEILING, (
        f'{len(skipped)} fences marked test="skip" exceeds the ceiling of '
        f"{SKIP_CEILING}:\n" + "\n".join(skipped) + "\n"
        "Complete them into runnable state, or raise SKIP_CEILING in the same "
        "diff with the justification in review."
    )
