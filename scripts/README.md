# scripts/ — the tool workshop

Purpose-built CLI utilities instead of generic shell pipelines. Each environment below has a
different job and a different lifecycle. `/ai:tool` builds and manages what lives here.

| Environment | For                                                         | Lifecycle            |
| ----------- | ----------------------------------------------------------- | -------------------- |
| `go/`       | Reusable, compiled CLIs. Speed, reliability, single binary. | Maintained           |
| `py/tools/` | Reusable Python CLIs. Ecosystem-heavy work.                 | Maintained           |
| `py/lab/`   | Disposable single-file scripts. Exploration and research.   | Pruned on sight      |

There is no shell environment. The legacy `sh/` set was deliberately shrinking and has now
been ported away entirely — the point of this workshop is to stop depending on generic
OS-level commands. A new shell script here is a port candidate before it is even written.

## Choosing

The full decision procedure is in `/ai:tool`. The short version:

- **Unknown shape, changing fast, one-off?** → `py/lab/`, a single PEP 723 file.
- **Recurring, ecosystem-heavy (scraping, parsing, dataframes)?** → `py/tools/`.
- **Recurring, hot loop, large inputs, needs to be a binary?** → `go/cmd/`.
- **Genuinely balanced?** → start in `py/lab/`, promote if it survives.

Promotion is one-directional and cheap: `lab/` → `tools/` → `go/`. Nothing gets demoted; it
gets deleted.

## Running things

```bash
# Go
cd scripts/go && go build -o bin/ ./...      # binaries land in bin/ (gitignored)
cd scripts/go && go run ./cmd/ensure tokei   # or run directly

# Python — reusable
cd scripts/py && uv sync --all-packages      # --all-packages: root sync alone skips members
cd scripts/py && uv run mdlinks .canon

# Python — disposable
uv run scripts/py/lab/<name>.py              # inline deps, ephemeral env, no lockfile impact
```

## What's here now

| Tool                    | Language | Job                                                    |
| ----------------------- | -------- | ------------------------------------------------------ |
| `go/cmd/ensure`         | Go       | Install an adopted third-party CLI (currently `tokei`) |
| `py/tools/mdlinks`      | Python   | Find broken relative links in Markdown                 |

## Adopted tools

Not everything in the workshop is written here. Counting lines of code is
[tokei](https://github.com/XAMPPRocky/tokei), adopted rather than built:

```bash
cd scripts/go && go run ./cmd/ensure tokei   # installs it if missing
tokei . --files --sort lines                 # the file-size review in .canon/checks.md
```

Before building any tool, check whether a mature one already exists — `/ai:tool` makes that a
hard gate, and `cmd/ensure` is where an adopted tool gets wired in so it is always available.
