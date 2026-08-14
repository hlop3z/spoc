# Tasks: honest README quickstart, enforced

## 1. Widen the gate

- [x] 1.1 `README.md` added to the fence collection in `tests/test_docs_examples.py`
  (`find_examples(DOCS_DIR, README)`), keeping one runner, one `SKIP_CEILING`, one
  `#>` output convention. `test_examples_are_collected` now also asserts the README
  contributed fences, so a path regression cannot silently drop the front page.
- [x] 1.2 Red-before-green was taken out of order: the README was rewritten first
  (positioning work, below), so the gate never saw the paste-trap version. The
  equivalent proof is on record — assembling the README's tree and running it was
  verified to execute and print `/blog/post <class 'apps.blog.models.Post'>`, and
  the collection assertion pins that the fences are seen.

## 2. Rewrite the Quick Start

- [x] 2.1 Four titled frames — `framework.py`, `apps/blog/models.py`,
  `config/spoc.toml`, `main.py` — each carrying its filename as the first line so
  GitHub and PyPI show it (fence `title=` renders invisibly outside MkDocs).
- [x] 2.2 The composition root shows `start()`, `resolve("models:blog.post")`,
  `objects.models.blog.post`, and the `by_kind` surface-projection loop.
- [x] 2.3 Wired to the existing tree harness: `test_page_project[README.md]`
  assembles the four files and runs `main.py`. Zero new skip markers.
- [x] 2.4 Surrounding prose adjusted.

## 3. Audit the mirror

- [x] 3.1 `docs/docs/index.md` does not have the paste-trap shape — its blocks were
  already framed by file. It gained one boundary sentence instead (what SPOC does
  not replace), matching the README's.

## 4. Positioning (scope added mid-change — see proposal)

- [x] 4.1 README rewritten for adoption: recognizable hook, derived-output demo,
  what-SPOC-decides boundary table, "why not just…?" objections, an honest
  should-you-use-it section that names who should not.
- [x] 4.2 Trimmed for beginners — the CLI-plumbing excerpt and the densest feature
  prose came out; every section is scannable.

## 5. Validation (Rule 6 — `.canon/checks.md`)

- [x] 5.1 `uv run pytest` — docs snippet suite now includes README.
- [x] 5.2 `cd scripts/py && uv run mdlinks ../..` and `cd docs && uv run mkdocs build
  --strict`.
- [x] 5.3 `uv run ruff format --check .` and `uv run ruff check`.
