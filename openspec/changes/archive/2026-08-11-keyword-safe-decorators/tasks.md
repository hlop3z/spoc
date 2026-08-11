# Tasks

## 1. Confirm the defect and its blast radius

- [x] 1.1 Reproduce: generate into a temp directory with `--kinds class` and confirm both
      `framework.py` and the per-kind app module fail to compile.
      → Confirmed against the shipped CLI: `compileall` reported two `SyntaxError`s,
      `from framework import class` (app module, line 3) and
      `class = framework.kind("class")` (declaration, line 8). Note `spoc init` itself
      exited 0 and printed the "Next: python main.py" banner — the failure is silent until
      the reader follows it.
- [x] 1.2 Confirm the kind itself is legal everywhere else — the identity grammar accepts
      `class`, and `importlib.import_module` loads a module file named `class.py` — so the
      fix belongs at the point the name becomes source text, not at validation.
      → Both hold. `SEGMENT_PATTERN` is `^[a-z][a-z0-9_]*$`, which `class` satisfies, and
      the loader's only import path is `importlib.import_module`, which has no keyword
      restriction. The post-fix project boots and registers `class:core.example`.
- [x] 1.3 Confirm `decorator_names` is the only derivation of the variable name.
      → It is: `operations.py:87` builds the declaration lines from it, and `build_plan`
      binds `$decorator` from the same call. No template spells a name itself.

## 2. Make the derivation total

- [x] 2.1 Add `_escape_keyword`: a single trailing underscore for a name `keyword.iskeyword`
      claims, per PEP 8 (design ADR-1).
- [x] 2.2 Rewrite `decorator_names` as three ordered steps — propose the singular, fall back
      to the kind on a pre-escape collision, then escape — and drop `keyword.iskeyword`
      from the fallback condition, since escaping now handles it uniformly.
- [x] 2.3 Append underscores until each escaped name is unused, so escaping cannot
      introduce a duplicate binding (design ADR-2).
- [x] 2.4 Update the `decorator_names` docstring to state the three steps and the reason
      for each, replacing the "two cases fall back" description that no longer holds.
      → Deviation from the plan's shape, not its content: the dict comprehension became an
      explicit loop. The uniquing pass needs the set of names already handed out, which a
      comprehension cannot carry, and splitting it into a second comprehension would have
      stated the fallback rule in two places.

## 3. Pin the behaviour

- [x] 3.1 Update `test_decorator_falls_back_to_the_kind_when_singular_is_unsafe`: `ifs` now
      yields `if_`, not `ifs`. Renamed to `test_decorator_is_kept_legal_and_distinct`,
      which is what it now asserts — the old name described the remedy, and the remedy is
      no longer always a fallback.
- [x] 3.2 Add a test generating with a keyword kind (`class`) that compiles every generated
      `.py` file, so the assertion is "it parses", not "it contains a string".
      → `test_a_kind_named_for_a_keyword_generates_parsable_python` compiles the whole tree
      via `rglob("*.py")`, which would also have caught the defect in any file added later.
- [x] 3.3 Add a test for the post-escape collision pair (`class`, `class_`) asserting two
      distinct decorator names.
- [x] 3.4 Keep the collision and unchanged-name cases (`view`/`views`, `status`,
      `middleware`) asserted — the pre-escape fallback must not regress.

## 4. Docs and record

- [x] 4.1 `docs/docs/learn/framework.md` states the singular rule; state the keyword escape
      beside it (Rule 8).
- [x] 4.2 `CHANGELOG.md` — an `Unreleased / Fixed` entry naming the keyword case and the
      `ifs` → `if_` behaviour change.
- [x] 4.3 Record ADR-1 and ADR-2 in `DECISIONS.md`.

## 5. Validate

- [x] 5.1 Run the checks in `.canon/checks.md`; report anything not runnable as unverified.
      → `task check` green end to end: ruff format (101 files), ruff check, `go vet`, `ty`,
      690 tests (6 docs skips, at the ceiling), Go build, `mdlinks`, strict `mkdocs build`,
      `apicheck` (0 fatal, 1 pre-existing `unverifiable` for the `schema` kind), `apidiff`
      (0 surface changes — the fix is behavioural, not a surface change; the in-flight
      `extract_archive` withdrawal is unrelated and unchanged). Nothing unverified.
