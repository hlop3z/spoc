---
name: "AI: Tool"
description: Build and manage small CLI utilities in Go or Python — pick the language from project need, scaffold it, then promote or retire it
category: AI
tags: [ai, tooling, cli, go, python]
---

Build a focused command-line tool instead of reaching for a generic shell pipeline.

The goal is a **library of purpose-built CLIs** — each with one clear job, a composable
interface, and a path from throwaway experiment to maintained utility. Every tool built this
way is one less fragile `awk | sed | xargs` chain and one less thing that only works on one
machine.

**Input**: what the tool should do, in a sentence. Optionally a name. If the request is vague
about the job, ask before scaffolding — a tool with an unclear purpose is the thing this
command exists to prevent.

## Step 1 — Read the project before choosing anything

The right answer depends on **this** project, not on a default. Establish, in order:

1. **Does a tool already exist for this?** Check `scripts/go/cmd/`, `scripts/py/tools/`,
   `scripts/py/lab/`, and `scripts/sh/`. If something close exists, **extend it** rather than
   adding a near-duplicate (Rule 7). Two tools solving one problem is the failure mode here.
2. **Does a mature CLI already solve this? — HARD GATE.** **Search the web before writing a
   line.** Do not answer this from memory: you will not remember the tool that already exists,
   and "I didn't know of one" is not the same as "there isn't one". `ripgrep`, `jq`, `fd`,
   `tokei`, `scc`, `curl`, `hyperfine`, `dust` and hundreds more exist — rebuilding any of
   them is a defect, not a shortcut.

   Build only when the job is *this project's* specific composition of steps, not a commodity
   operation. If a mature tool exists, the work is to **adopt** it: add it to
   `scripts/go/cmd/ensure` so it installs on any machine, and record the choice in
   `DECISIONS.md`. "It isn't installed here" is never a reason to reimplement something.

   When the call is close, run `/ai:decide` and record it.
3. **What does the project already use?** A repo that is mostly Go should not grow a Python
   tool for a job Go handles fine, and vice versa. Existing language, existing dependencies,
   and what the team already maintains all outweigh a marginal technical preference.
4. **Which workspaces exist?** `scripts/go/` and `scripts/py/` may not be present in a project
   installed from this template. Create the missing one from `scripts/README.md` before
   scaffolding into it.

Announce the findings in one line before proceeding: "No existing tool; project is Go-heavy;
building reusable Go tool `<name>`."

## Step 2 — Disposable or reusable?

| Signal                                                             | Verdict        |
| ------------------------------------------------------------------ | -------------- |
| Exploring, the shape is unknown, it will change within the hour     | **disposable** |
| One-off data gathering, a research question, a spike                | **disposable** |
| Solves a recurring problem you will hit again                       | **reusable**   |
| Something else will depend on its output or exit code               | **reusable**   |
| You cannot yet say whether it recurs                                | **disposable** |

Default to **disposable**. A disposable tool that proves itself gets promoted in minutes; a
premature package is dead weight that still has to be maintained. Promotion is cheap,
demotion never happens.

## Step 3 — Go or Python?

Weigh performance, complexity, iteration speed, and long-term maintainability — against what
Step 1 found about the project.

| Signal                                                          | Go  | Python |
| ---------------------------------------------------------------- | :-: | :----: |
| Runs in a loop, on large inputs, or where startup latency matters | ✔  |        |
| Must ship as a single binary with no runtime on the target        | ✔  |        |
| Long-lived: will be maintained, extended, depended on             | ✔  |        |
| Concurrency, retries, streaming I/O, process orchestration        | ✔  |        |
| Strict behavior under failure matters more than writing speed     | ✔  |        |
| The shape is unknown and will change every few minutes            |     |   ✔   |
| Leans on an ecosystem library (scraping, dataframes, parsing, ML) |     |   ✔   |
| One-off extraction, transformation, or research                   |     |   ✔   |
| Glue around Python that the project already has                   |     |   ✔   |

**When it is genuinely balanced: start in Python `lab/`, and promote to Go if it survives.**
That ordering is deliberate — iteration speed is worth more while the design is uncertain, and
reliability is worth more once it is not.

Disposable + Go is a valid but rare combination; it usually means the real driver is input
size. Prefer Python `lab/` unless the run time actually hurts.

## Step 4 — Scaffold

### Reusable Go tool → `scripts/go/cmd/<name>/`

One `main.go` per tool, cobra for the interface, shared helpers in `internal/`.

```bash
cd scripts/go
mkdir -p cmd/<name>
# write cmd/<name>/main.go using cobra (see cmd/ensure for the reference shape)
go mod tidy && go build -o bin/ ./... && go vet ./...
```

Logic that another tool could reuse goes in `internal/<topic>/`, not in `main.go` — Rule 2
applies inside `scripts/` too, and `main.go` is an adapter.

### Reusable Python tool → `scripts/py/tools/<name>/`

A uv workspace member with cyclopts and a console-script entry point.

```bash
cd scripts/py
uv init --lib tools/<name>        # then set the [project.scripts] entry point
uv add --package <name> cyclopts
uv sync --all-packages
uv run <name> --help
```

Keep the logic in `src/<name>/core.py` as plain functions and let `cli.py` be a thin adapter
over it. `tools/mdlinks` is the reference shape.

### Disposable Python tool → `scripts/py/lab/<name>.py`

A single file with PEP 723 inline dependencies — **not** a workspace member, so it never
touches the shared lockfile.

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""Purpose: <one line>. Created: <YYYY-MM-DD>. Expires: <when this stops being useful>."""
```

Run it with `uv run scripts/py/lab/<name>.py`. The docstring header is required — an
undated lab script with no stated purpose cannot be pruned or promoted later.

## Step 5 — Interface conventions (every tool, both languages)

- **One job.** If the description needs an "and", consider two tools or two subcommands.
- **Composable**: data to stdout, diagnostics to stderr, meaningful exit codes (`0` success,
  non-zero failure). A tool that gates a check must exit non-zero when it finds a problem.
- **`--json`** wherever output could be consumed by another tool. Human-readable stays default.
- **Read from a path argument or stdin**; never hardcode a location.
- **No side effects without a flag.** Deleting, overwriting, or uploading is opt-in.
- **`--help` explains the job**, not just the flags.

## Step 6 — Validate, then record

Rule 6 applies. At minimum, actually run the thing:

- Go: `go build ./... && go vet ./...`, then run it against real input and a failing case.
- Python: `uv run <name> --help`, then a real case and a failing case.
- Confirm the exit code is non-zero on failure — this is the most commonly broken contract.

Then:

- Reusable tool that a check should use → add a row to `.canon/checks.md`.
- Tool that replaced a shell script → **delete the shell script** (Rule 5; git history keeps it).
- Anything that changed how the workspace is used → update `scripts/README.md` (Rule 8).
- Commit per Rule 3: `feat:` for a new tool, `chore:` for a lab script.

## Promotion and retirement

**Promote** `lab/<name>.py` → `tools/<name>/` when it has been used more than twice, or
something now depends on it. Split the logic into `core.py`, add the cyclopts adapter, add the
entry point, delete the lab file.

**Promote Python → Go** when it has become slow, needs to be a single binary, or its failure
modes now matter. Port it; don't keep both (Rule 7).

**Retire** on sight. A lab script past its stated expiry, or a tool nothing calls, gets
deleted. Report what you removed. This folder is a workshop, not an archive — the discipline
is the same promote-or-discard rule that governs `.canon/`.

## Guardrails

- Never scaffold before Step 1. Duplicating an existing tool is the main failure mode.
- **Never reinvent the wheel.** Search first, every time. This repo has already lost a day to
  a hand-written line-counter that `tokei` and `scc` both already did better — see
  `DECISIONS.md`. Adopting and wiring the tool into `cmd/ensure` is nearly always the smaller
  job than building, and it is always the more correct one.
- Disposable by default; reusable is earned.
- A tool with no clear one-sentence job doesn't get built. Ask instead.
- Lab scripts are single files with inline deps. The moment one needs a package layout, it is
  asking to be promoted.
- Don't add a dependency to the Go module or the uv workspace for a disposable experiment.
