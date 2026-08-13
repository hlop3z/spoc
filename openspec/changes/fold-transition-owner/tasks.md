## 1. Pin the current behaviour before changing it

- [x] 1.1 Add a failing test: a task created *before* an `astart`/`ashutdown` transition,
      awaiting on the same event loop, invokes `astart` on that framework and must receive
      the "transition already in progress" error — not the reentrancy error
- [x] 1.2 Add a passing-today test that must stay passing: a task spawned *by* a lifecycle
      hook invokes `astart`/`ashutdown` on the framework whose transition spawned it and
      receives the reentrancy error
- [x] 1.3 Confirm 1.1 fails for the expected reason (message says "inside a lifecycle
      transition") and 1.2 passes, before touching `framework.py`

## 2. Fold the mechanism

- [x] 2.1 `_refuse_reentry` decides membership with `self._inside_transition()` instead of
      comparing `_transition_owner` to `threading.get_ident()`
- [x] 2.2 Drop "already running on this thread" from the reentrancy message, keeping the
      offending call's label and the phrase "inside a lifecycle transition" that the two
      existing tests assert on
- [x] 2.3 Delete the `_transition_owner` attribute: its declaration in `__init__`, its
      assignment in `_begin_transition`, and its clearing in `_end_transition`
- [x] 2.4 Remove the now-dead `threading.get_ident` usage; keep the `threading` import only
      if `threading.Lock` still needs it

## 3. Make the code say what is now true

- [x] 3.1 Update the `_transitioning` docstring, which currently contrasts itself against
      `_active_transitions` for reads only — both questions now route through the marker
- [x] 3.2 Qualify the `_active_transitions` module comment: spawned work inherits the marker
      for tasks and `asyncio.to_thread`, not for a bare `threading.Thread`
- [x] 3.3 Update the `Framework` class docstring paragraph on reentrancy so it no longer
      describes the rule in terms of the calling thread
- [x] 3.4 Update `docs/architecture/kernel.md` invariant 9 — it names no mechanism, so the
      edit is scope instead: the inside/outside test governs transitions as well as reads,
      and a caller the transition never invoked is told it may retry

## 4. Validate

- [x] 4.1 `task check` exits 0 — every gate row in `.canon/checks.md`
- [x] 4.2 The two pre-existing reentrancy tests pass unchanged, with no edit to their
      assertions
- [x] 4.3 `apidiff` reports no added, removed, or breaking entries for this change, and no
      `violated:` line — output is identical to the pre-change state; the one `added:` line
      is the previous change's error type, which the v0.8.0 baseline predates
- [x] 4.4 Confirm no remaining reference to `_transition_owner` anywhere in the repo —
      it survives only in this change's artifacts and the archived change's record
