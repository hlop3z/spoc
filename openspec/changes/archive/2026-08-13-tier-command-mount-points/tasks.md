## 1. Carry the notice on each mount point

- [x] 1.1 Add the `Provisional:` paragraph to `spoc/scaffold/cli.py`'s `register` docstring,
      stating the settling condition: a template-mounting framework outside this package, or
      SPOC committing to its parser choice.
- [x] 1.2 Add the same paragraph to `spoc/diagnostics/cli.py`'s `register`.
- [x] 1.3 Add the same paragraph to `spoc/projection/cli.py`'s `register`.
- [x] 1.4 Add the same paragraph to `spoc/stubs/cli.py`'s `register`.
- [x] 1.5 Confirm each notice contains the exact phrase the checker matches and a further
      sentence of substance — a bare hedge is a fatal finding, not a warning.

## 2. Publish each mount point from its package

- [x] 2.1 Re-export `register` from `spoc/scaffold/__init__.py` under a comment saying what the
      mount is for, so the export's reason is readable where it is made.
- [x] 2.2 Re-export `register` from `spoc/diagnostics/__init__.py`.
- [x] 2.3 Re-export `register` from `spoc/projection/__init__.py`.
- [x] 2.4 Re-export `register` from `spoc/stubs/__init__.py`.
- [x] 2.5 Check each package's existing `__all__` has no name collision with `register`, and
      that importing the package does not now import the parser module eagerly in a way the
      kernel's import cost cares about.

## 3. Verify the tiers resolve as intended

- [x] 3.1 Run `apicheck` and confirm all four resolve to `provisional`, with no element left
      unresolved and no bare-hedge finding.
- [x] 3.2 Run `apidiff` and confirm the four appear as additions at `provisional`, and that no
      new breakage is introduced by this change.
- [x] 3.3 Confirm the shipped `spoc` program still mounts all four through the same functions —
      the extension point must not acquire a privileged second path.

## 4. Make the documentation say the same thing

- [x] 4.1 Replace the tiering **warning** in `docs/docs/how-to/ship-a-framework.md` with a tier
      **statement**, and extend the page to the inspection commands so the downstream story
      covers generation and validation rather than generation alone.
- [x] 4.2 Add the four elements to the stability page's provisional listing, if that page
      enumerates elements rather than deriving them.
- [x] 4.3 Fix `spoc/cli.py`'s module docstring, which lists three mounted surfaces and omits
      `stubs` even though it mounts it.
- [x] 4.4 Confirm every Python fence added or changed in the docs runs under
      `tests/test_docs_examples.py`.

## 5. Close the question and validate

- [x] 5.1 Rewrite the `DECISIONS.md` open-question section as a decision: what was chosen, that
      it was widened from one mount point to four, and why `provisional` over `public`.
- [x] 5.2 Run the full gate and read `task check`'s exit code directly, not a pipeline's.
- [x] 5.3 Commit by intent per Rule 3 — the notices and exports, the docs, and the decision are
      separate concerns.
