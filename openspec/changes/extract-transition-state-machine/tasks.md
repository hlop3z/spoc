## 1. Pin the property before moving anything

- [ ] 1.1 Add a test asserting a racing asynchronous transition fails with the
      already-in-progress error rather than waiting for the in-flight one to settle
- [ ] 1.2 Add a test asserting unrelated scheduled work makes progress while that refusal
      happens — the assertion that separates "does not deadlock" from "does not block"
- [ ] 1.3 Confirm both tests pass against the current open-coded implementation. A test
      that only passes after the refactor is testing the refactor, not the property

## 2. Build the gate

- [ ] 2.1 Create `src/spoc/core/transition.py` with `TransitionGate`, owning the lock, the
      in-flight label, and the module-level `ContextVar[frozenset[TransitionGate]]`
- [ ] 2.2 Implement the membership and refusal reads: `inside`, `refuse_reentry(label)`,
      `refuse_racing_read(identifier)`
- [ ] 2.3 Implement one private begin/end pairing, and expose `hold(label)` (blocking) and
      `claim(label)` (non-blocking) as context managers over it
- [ ] 2.4 Give the already-in-progress message one definition, replacing the literal
      currently spelled at both asynchronous call sites

## 3. Delegate from Framework

- [ ] 3.1 Construct the gate in `Framework.__init__`; remove `_transition_lock` and
      `_transitioning` from the framework's own state
- [ ] 3.2 Point the four read accessors at `refuse_racing_read`
- [ ] 3.3 Move `start` and `shutdown` onto `hold`
- [ ] 3.4 Move `astart` and `ashutdown` onto `claim`, deleting both hand-written
      acquire/begin/`finally` sequences
- [ ] 3.5 Delete the six migrated members and the module-level context variable from
      `framework.py`

## 4. Verify nothing moved that should not have

- [ ] 4.1 Run the full suite with no test file modified except the additions from group 1
- [ ] 4.2 Run `uv run ruff format --check .`, `uv run ruff check`, `uv run ty check`, and
      `uv run mypy`
- [ ] 4.3 Run `apicheck` and `apidiff`; both MUST report no surface delta
- [ ] 4.4 Confirm `framework.py` is under the 600-line review threshold and record both
      line counts
- [ ] 4.5 Re-run coverage over `src/spoc/core/transition.py` and confirm no line is
      newly unreached

## 5. Documentation (Rule 1, Rule 8)

- [ ] 5.1 Update `docs/architecture/kernel.md`: show the gate as a collaborator and the
      inward-only edge from `framework.py`
- [ ] 5.2 Add the CHANGELOG entry under `1.0.0`, naming the added requirement rather than
      the refactor — the requirement is the part a reader can act on
- [ ] 5.3 Run `mdlinks` and `mkdocs build --strict`
