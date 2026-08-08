# Validation commands

The canonical commands for Rule 6. **Use these exact commands** — don't improvise an
equivalent, and don't guess at a package manager the project doesn't use.

This file is per-project. The template ships it nearly empty on purpose: fill a row in the
moment you first discover the real command, so the next session doesn't rediscover it.

| Check             | Command                                                | Status                                                                    |
| ----------------- | ------------------------------------------------------ | ------------------------------------------------------------------------- |
| Formatter         | `uv run ruff format --check .`                         | Python only. Markdown is unformatted — the ruff rule set drops `*.md` from `include` on purpose (see `pyproject.toml`). |
| Linter            | `uv run ruff check` · `cd scripts/go && go vet ./...`  | Python + Go workspace                                                     |
| Type checker      | `uv run ty check`                                      | Python (ty)                                                               |
| Unit tests        | `uv run pytest`                                        | `testpaths` pins `tests/` in pyproject.toml — one suite covers the kernel, the scaffold, and `spoc.formats` |
| Integration tests | `uv run pytest tests/test_framework.py`                | Filesystem-fixture framework tests (subset of unit run)                   |
| Build             | `cd scripts/go && go build -o bin/ ./...`              | Go workspace only                                                         |
| Doc links         | `cd scripts/py && uv run mdlinks ../..`                | Fails non-zero on any broken relative Markdown link (Rule 8)              |
| API surface       | `cd scripts/py && uv run apicheck ../..`               | Fails when the real surface and `[tool.spoc.stability]` disagree, or a `provisional` element omits its notice. Static (griffe) — needs no install of `spoc` itself. Kinds it cannot observe are reported `unverifiable`, never silently passed. |
| Tool tests        | `cd scripts/py && uv run pytest tools/`                | The workshop tools' own suites. The Unit tests row cannot reach them — `testpaths = ["tests"]` pins it to the package suite, and the tools are a separate workspace. These test the code that gates everything else, so they get their own row. |
| File-size review  | `tokei . --files --sort lines`                         | **Review aid, not a gate** — `tokei` always exits 0 and the thresholds in `.canon/guidelines.md` are a judgement call, so `task check` does not run it. Any language, largest first; run it as `task size`. Missing? `cd scripts/go && go run ./cmd/ensure tokei` |

A row marked "not yet defined" is a real answer: that check is **unverified** and Rule 6 says
to report it as such. It is not permission to skip it silently.

## Running them

`task check` runs every gate row above, in order, with the same scope. The one row it does not
run is **File-size review**, which is marked a review aid rather than a gate for the reason
given in its Status cell. `Taskfile.yml` and `.github/workflows/ci.yml` are both derived from
this table — if you add a check to one, add it to all three, or `task check` stops being the
gate it claims to be.

The commands in the table remain the source of truth: a Taskfile task that disagrees with a
row is a defect in the Taskfile, not a second opinion.

The canon's usual advice is to point at a project's existing runner rather than copy commands
into this file — one home. This project inverts that on purpose: two consumers derive from
these commands (the Taskfile and CI), and the table is the only place that also records *why*
each command is shaped the way it is. Pointing at `Taskfile.yml` would put the reasons nowhere.
