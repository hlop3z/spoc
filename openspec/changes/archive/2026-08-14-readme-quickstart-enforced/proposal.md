# Honest README quickstart, enforced by the docs gate

## Why

The README Quick Start decorates a class inline and then resolves
`models:blog.post` — which only works when the class lives in `apps/blog/models.py`,
so a reader pasting the block verbatim gets a resolution error on first contact with
the library. The defect survived because the docs-examples gate
(`tests/test_docs_examples.py`) executes fences under `docs/docs/` only; the README —
the most-read page the project publishes, and the PyPI long-description — is the one
document nothing verifies. The `documentation-integrity` spec already demands that
"every code example in the published documentation" executes; the implementation
falls short of the spec's own scope.

A second problem surfaced while this change was in flight, and is folded in here
rather than split: the README was written for a reader who already knows why a
structural kernel exists. Review feedback ranked "users don't understand the value
proposition" as the project's largest adoption risk, ahead of anything technical —
a reader could not tell in a minute whether SPOC competes with FastAPI, replaces
Django, or sits underneath both.

## What Changes

- The README Quick Start is restructured to be honest: the decorated class is shown
  in its `apps/blog/models.py` home, and the boot-and-resolve script is shown
  separately, mirroring the docs quickstart's presentation. No fence shows an inline
  decoration flowing into a successful resolve.
- The README is repositioned for a first-time reader: a hook built on frameworks
  they already know, the derived-CLI demo as the payoff, an explicit boundary table
  (what SPOC decides / what stays yours), a "why not just…?" table answering imports,
  entry points, pluggy, Django, and DI containers, and a should-you-use-it section
  that names who should *not*. Trimmed overall — density was part of the defect.
- The docs-examples runner is extended to `README.md`, so every Python fence in it
  runs against a harness-supplied project tree or carries an explicit justified skip
  marker, counted against the existing skip ceiling.
- `docs/docs/index.md` is audited for the same paste-trap and fixed the same way if
  it mirrors the README.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `documentation-integrity`: the examples-execute requirement's scope is made
  explicit — "published documentation" includes the repository README (the
  distribution long-description), not only the documentation site's pages.

## Impact

- `README.md` — Quick Start restructure and a positioning rewrite of the surrounding
  sections.
- `tests/test_docs_examples.py` — fence collection extended to `README.md`.
- `docs/docs/index.md` — audit found no paste-trap; gained the same boundary
  sentence the README now carries.
- No source code, dependency, or API changes. The docs build and PyPI
  long-description rendering are unaffected by fence semantics.
