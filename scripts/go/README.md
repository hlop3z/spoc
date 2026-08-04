# Go workspace — reusable compiled CLIs

One module, one binary per `cmd/` subdirectory. Tools here are meant to be maintained.

```
go.mod              module tools
cmd/<name>/main.go  one binary per directory — the CLI adapter
internal/<topic>/   shared logic; anything two tools could both use
bin/                build output (gitignored)
```

**Single module, not a `go.work` multi-module workspace.** These are small tools that share
helpers and are never published independently, so one `go.mod` gives them a shared dependency
set and a single `go build ./...`. If a tool ever needs its own release cadence, that is the
moment to split it out — not before.

The module is named `tools` rather than a URL because nothing here is `go get`-able. Rename it
to the repository path if that ever changes.

## Conventions

- `main.go` is an **adapter** (Rule 2). Real logic goes in `internal/` where it can be tested
  without the CLI and reused by a second tool.
- cobra for the interface — subcommands, generated help, and completions for free.
- Data to stdout, diagnostics to stderr, non-zero exit on failure.
- `--json` on anything another tool might consume.

## Working on it

```bash
go build -o bin/ ./...   # -o bin/ keeps artifacts out of the source tree
go vet ./...
go run ./cmd/ensure tokei
go mod tidy
```

Build with `-o bin/`. A bare `go build ./...` drops binaries into the current directory, where
they are easy to commit by accident.

`cmd/ensure` is the reference shape for a new tool: a cobra adapter in `cmd/`, the actual work
in `internal/ensure/`. It is also where an **adopted** third-party CLI gets registered, so that
"not installed" never becomes a reason to reimplement something mature.
