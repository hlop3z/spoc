# Tasks — Reunify the Formats Distribution

## 1. Move the code

- [x] 1.1 Move `packages/spoc-formats/src/spoc_formats/` to `src/spoc/formats/`
      (five modules + `py.typed` travels implicitly with the parent package);
      rename internal `spoc_formats` imports to `spoc.formats`
- [x] 1.2 Move `packages/spoc-formats/tests/test_formats.py` to
      `tests/test_formats.py`; update its imports
- [x] 1.3 Delete `packages/` entirely, including the member `pyproject.toml` and
      `README.md` (Rule 5 — superseded by this merge)

## 2. Packaging

- [x] 2.1 Root `pyproject.toml`: restore `[project.optional-dependencies]`
      (`yaml`, `xml`, `toml`, `query`, `full = ["spoc[yaml,xml,toml,query]"]`);
      remove `[tool.uv.workspace]` and `[tool.uv.sources]`; dev group
      `spoc-formats[full]` → `spoc[full]`; `testpaths` drops the packages entry;
      the ty override drops `packages/spoc-formats/tests/**`; update the comments
      that state the two-distribution story
- [x] 2.2 `uv sync` regenerates the lockfile; verify the extras install and the
      formats suite still exercises real codecs

## 3. Boundary becomes a tested contract

- [x] 3.1 Pin the boundary in `tests/test_formats.py`'s dependency-footprint
      section (the established home — no new file): a fresh-interpreter import
      of `spoc` loads no `formats` module and no optional codec dependency;
      `FormatError` is not a subclass of `SpocError`; an AST scan proves no
      kernel module imports the data surface

## 4. CI / Release

- [x] 4.1 `release.yml` (and `ci.yml` if it references the workspace): build one
      artifact (`uv build`), publish one package; invert the wheel check —
      `spoc.formats` MUST be inside the kernel wheel

## 5. Docs, example, changelog, decisions (Rule 8)

- [x] 5.1 `docs/docs/advanced/data-formats.md`, root `README.md`,
      `docs/architecture/kernel.md`: one install/import story
      (`pip install "spoc[full]"`, `from spoc import formats`)
- [x] 5.2 `examples/data_app.py` imports `spoc.formats`
- [x] 5.3 Rewrite the CHANGELOG 0.5.0 formats entry: contained subpackage with
      extras, boundary test-enforced, one artifact
- [x] 5.4 `DECISIONS.md`: mark the multi-distribution ADR superseded, pointing at
      this change
- [x] 5.5 `.canon/checks.md`: update the pytest row's note (single suite location)

## 6. Validation (Rule 6 — `.canon/checks.md`)

- [x] 6.1 Full gates: pytest (both suites, now one tree), ruff format/check, ty,
      mdlinks, mkdocs build, `uv build` + wheel content check
- [x] 6.2 `openspec validate --all` passes
