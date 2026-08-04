# Python workspace — uv

Two shapes with deliberately different lifecycles: packaged tools that are maintained, and
single-file lab scripts that are not.

```
pyproject.toml      workspace root — holds the member globs and the shared lockfile
uv.lock             shared across all members; commit it
tools/<name>/       workspace members — reusable, packaged, console-script entry points
lab/<name>.py       single-file PEP 723 scripts — disposable, NOT members
.venv/              shared environment (gitignored)
```

## Why lab/ is excluded from the workspace

A uv workspace member must have a `pyproject.toml` and enters the shared lockfile. That is
exactly wrong for a throwaway: it would make every experiment a dependency-resolution event,
and a deleted script would leave the lockfile inconsistent.

So `lab/` is listed under `exclude` in the root `pyproject.toml`. Lab scripts carry their own
dependencies inline via PEP 723 and run in an ephemeral environment:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "selectolax"]
# ///
"""Purpose: <one line>. Created: <YYYY-MM-DD>. Expires: <when this stops being useful>."""
```

```bash
uv run scripts/py/lab/<name>.py --help
```

The docstring header is required. A lab script with no stated purpose or date cannot be pruned
or promoted with any confidence later — it just accumulates, which is what the canon's
promote-or-discard rule exists to prevent.

## Reusable tools

```bash
uv sync --all-packages      # plain `uv sync` syncs only the root and skips the members
uv run mdlinks --help
uv add --package mdlinks httpx
```

Each member keeps logic in `src/<name>/core.py` as plain functions, with `cli.py` as a thin
cyclopts adapter over it (Rule 2). `tools/mdlinks` is the reference shape.

## Promotion

A lab script earns a package when it has been used more than twice or something depends on it.
Split the logic into `core.py`, add the cyclopts adapter and the `[project.scripts]` entry
point, run `uv sync --all-packages`, and delete the lab file — don't keep both.
