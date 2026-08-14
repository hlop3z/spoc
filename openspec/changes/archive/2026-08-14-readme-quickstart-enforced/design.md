# Design: honest README quickstart, enforced

## Context

`tests/test_docs_examples.py` executes every Python fence under `docs/docs/` via
pytest-examples, with outputs mirrored in `#>` comments and skips capped by
`SKIP_CEILING`. `README.md` sits outside that collection, and its Quick Start contains
the one example in the project that cannot work as pasted: an inline-decorated class
resolved by an identifier that discovery only assigns to classes found in
`apps/<name>/<kind>.py`. The docs quickstart (`docs/docs/getting-started/quick-start.md`)
already presents this correctly with a file-layout frame.

## Goals / Non-Goals

**Goals:**

- A README whose every Python fence runs, under the same gate and skip discipline as
  the docs pages — the paste-trap class of defect becomes unrepresentable.
- A Quick Start that teaches the layout convention instead of hiding it, staying
  within roughly the current length.

**Non-Goals:**

- No new tooling: the runner, the tree harness, and the skip marker mechanism all
  exist; this change only widens collection and rewrites prose.
- No README redesign beyond the Quick Start section.
- No change to how `docs/site/` or PyPI render the README.

## Decisions

### Extend the existing runner, not a second one

`tests/test_docs_examples.py` gains `README.md` in its collected paths. One runner,
one skip ceiling, one output-mirroring convention — a parallel README-specific test
would be a second home for the same rule (Rule 7). Adopted tooling (pytest-examples)
already handles arbitrary Markdown paths; nothing is built, so there is no
`/ai:decide` call to record.

### Two-frame Quick Start

Frame 1: `apps/blog/models.py` containing the decorated class (annotated with the
identifier it produces). Frame 2: the composition root — declare kinds, `start()`,
resolve by string and by attribute walk, project a surface from `by_kind`. The
project-tree scenario in `documentation-integrity` already covers execution: the
suite supplies the tree through the test harness (`spoc.testing`), and the fences run
against it unmodified. Bash fences (`pip install`, `uvx spoc init`) are non-Python
and outside the runner's collection, as on the docs pages.

### Skips are a last resort

The target is zero new skip markers: both frames are runnable against a harness tree.
If a frame genuinely cannot run, it takes the existing explicit marker with a written
justification and counts against `SKIP_CEILING` — raising the ceiling requires its
own justification in the test.

## Risks / Trade-offs

- **README length**: two frames cost a few more lines than the current single block.
  Accepted — the current brevity is bought with a lie.
- **CRLF trap**: on Windows, `--update-examples` rewrites fences with CRLF line
  endings. Regenerate outputs on a POSIX shell or normalize afterward; the task list
  calls this out (known trap, recorded in project memory).
- **Divergence between README and docs quickstart**: both now show the same layout
  story in different depths. Both are executed by the same suite, so divergence in
  behavior is caught; divergence in prose is acceptable (different audiences).
