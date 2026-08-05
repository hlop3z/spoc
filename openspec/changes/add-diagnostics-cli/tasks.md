## 1. Subpackage and location

- [x] 1.1 Create `src/spoc/diagnostics/` with `core.py` result dataclasses (`Finding`, `CheckReport`, `RecordInfo`) and `locate.py` (`framework:framework` convention, `mod:attr` override, actionable miss error)
- [x] 1.2 Extend the kernel-containment AST test: `spoc.diagnostics` is an allowed importer of `spoc.testing`; kernel boundary unchanged; add the same containment test for `spoc.diagnostics` itself

## 2. Operations

- [x] 2.1 Implement `check(base_dir, framework_ref)` — config phase (`load_spoc_toml`/`validate_spoc_config`, mode-in-cascade) then dry-boot phase inside `spoc.testing` scopes, coroutine-hook refusal recorded and retried via `astart`, every finding collected
- [x] 2.2 Implement `list_records(base_dir, framework_ref, kind=None, namespace=None)` and `explain(identifier, base_dir, framework_ref)` over an isolated boot
- [x] 2.3 Black-box tests for every spec scenario in `project-diagnostics/spec.md` (clean pass + no residue, unresolvable app, config precision, coroutine flag, exit codes, enumeration + facet narrowing + unknown kind, explain known/unknown, convention/override/miss, library-CLI parity)

## 3. Composed CLI

- [x] 3.1 Create `src/spoc/cli.py` (`spoc` program) and refactor `spoc.scaffold.cli` into `register(subcommands)`; mount `init`, `check`, `list`, `explain`; repoint `[project.scripts]` to `spoc.cli:main`
- [x] 3.2 Update scaffold CLI tests to the composed surface; add CLI-adapter tests for the three new subcommands (rendering + exit codes only — logic is tested at the operations layer)
- [x] 3.3 Full validation per `.canon/checks.md` — all green, coverage not regressed

## 4. Docs

- [x] 4.1 CLI docs page covering check/list/explain (+ the "check imports your apps" caveat) and nav entry; README feature bullet
- [x] 4.2 Architecture diagram: fourth contained subpackage and the composed CLI entry (Rule 1/8)
