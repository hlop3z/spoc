# Contributing to SPOC

This file is a map, not a rulebook. Everything it points at is the real source of truth, and
none of it is restated here.

## Setup

SPOC requires **Python 3.12+** and uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-groups
```

The published package has **zero runtime dependencies** — `dependencies = []` in
`pyproject.toml`. That is an invariant, not a current state: a change that adds one needs to
justify itself as an architectural decision first. Everything under `[dependency-groups]` is
dev- or docs-only and never reaches an installer of `spoc`.

## Before you open a pull request

Run the validation suite. The canonical commands live in [`.canon/checks.md`](.canon/checks.md)
— formatter, linter, type checker, tests, the Go workspace build, and the doc-link check. CI
runs exactly those, so a green local suite means a green pipeline.

`task check` runs that suite for you — same commands, same repo-wide scope — so a green
`task check` means a green pipeline. Individual tasks (`task lint`, `task format`,
`task test:fast`) run one check each for the inner loop. `.canon/checks.md` stays the source
of truth; when a task disagrees with it, the task is wrong.

Ruff's rule selection is pinned explicitly in `pyproject.toml` rather than inherited from
ruff's defaults, so a toolchain upgrade cannot silently change what CI enforces. If a new
ruff release surfaces findings that shouldn't be enforced here, change that config in the
same pull request and say why — don't scatter `# noqa`.

### Editing the docs? The snippets are tested

Every Python fence under `docs/docs/` is in exactly one of three states, and silence is
not one of them — `tests/test_docs_examples.py` enforces this:

1. **Standalone**: runs as-is; printed output must appear as `#> ` comments (regenerate
   with `uv run pytest tests/test_docs_examples.py --update-examples` — on an **LF**
   checkout only; the updater corrupts CRLF files, see the module docstring).
2. **Project file** (`title="path"`): written into a per-page project, in page order, and
   run through the page's `title="main.py"` entry — so show complete files, never
   fragments.
3. **Marked** (`test="skip"` on the fence line): display-only, counted against an explicit
   ceiling in the test module. Raising the ceiling is a reviewed decision, not a reflex.

The API reference derives its member lists from `__all__` and the CLI page captures the
real `--help` at build time — don't hand-edit those listings; build the docs instead
(`task docs:check`).

## How work is organized

Changes are driven through **OpenSpec**, governed by a canon of engineering rules in
[`.canon/`](.canon/README.md); [`CLAUDE.md`](CLAUDE.md) describes the pipeline end to end.
A small fix doesn't need that machinery, but for anything that changes behavior the rules
still apply — most importantly:

- **Behavior contracts live in `openspec/specs/`**, not in code comments. If you change what
  the kernel guarantees, the spec changes with it.
- **Docs that contradict the code are defects** ([Rule 8](.canon/rules/08-docs.md)) — fixed in
  the same change set, not later.
- **Architecture is drawn, not described** ([Rule 1](.canon/rules/01-diagrams.md)) — see
  [`docs/architecture/kernel.md`](docs/architecture/kernel.md).
- **Never reinvent a mature tool.** Build-vs-adopt decisions are recorded as ADRs in
  [`DECISIONS.md`](DECISIONS.md).

## Commits

Conventional Commits, split by coherent intent, no attribution trailers. The full rule is
[`.canon/rules/03-commits.md`](.canon/rules/03-commits.md).

## Where things live

| Path        | What                                                             |
| ----------- | ---------------------------------------------------------------- |
| `src/spoc/` | The kernel. Pure core; adapters isolate anything external.        |
| `tests/`    | pytest suite; `testpaths` is pinned in `pyproject.toml`.          |
| `docs/`     | MkDocs site. `docs/architecture/` holds the Mermaid diagrams.     |
| `examples/` | Runnable example apps, linted the same as `src/`.                 |
| `openspec/` | Specs, in-flight changes, and the archive.                        |
| `scripts/`  | The tool workshop — see [`scripts/README.md`](scripts/README.md). |
| `.canon/`   | The engineering rules this project lives by.                      |

## Reporting issues

Open an issue at <https://github.com/hlop3z/spoc/issues>. For a bug, the most useful report
is the smallest `spoc.toml` plus declaration that reproduces it, and what you expected the
registry to contain.
