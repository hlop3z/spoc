## 1. Runtime navigation surface

- [x] 1.1 Implement the navigation object per design D1/D2: a dedicated attribute on
      the framework whose members are exactly the declared kinds, each yielding a
      namespace step, each yielding the same record `resolve` returns — lazy lookup
      against the registry, no materialization, no codegen. **Name settled:
      `framework.objects`** (design Open Questions records the declined candidates).
      A property rather than a stored attribute, so nothing needs keeping in sync,
      and it carries the same transition refusal every other read accessor does.
- [x] 1.2 Route per-segment failures through the registry's existing precision
      errors so an unknown kind/namespace/object names the segment and candidates —
      no duplicated error machinery. A component step composes the identifier and
      calls `registry.resolve`, so navigation and resolution are one lookup rather
      than two implementations tested into agreement.
- [x] 1.3 Apply the trailing-underscore reserved-word escape (design D4) at the
      runtime surface. The scaffold's private `_escape_keyword` moved to
      `core/identity.py` as `escape_keyword` — the grammar module is where spelling
      a segment as a Python name belongs, and the kernel cannot import from a
      surface package. Matching is forward (escape the candidates) so a project
      declaring both `class` and `class_` keeps both reachable.
- [x] 1.4 Unit tests, one per spec scenario of the first four requirements:
      reachability of every component, path=identifier parity, no double
      declaration, identical record, callable-not-invoked, unknown-object and
      unknown-kind precision, reserved-word kind navigable with identifier
      unchanged, and read-consistency during a lifecycle transition (reuse the
      transition-read test patterns).

## 2. Static description (emitter)

- [x] 2.1 Extend the manifest with the navigation grouping (kind → namespace →
      entries) derived from the existing entries — no second traversal of the
      registry. A property on `Manifest`, so the regrouping stays out of the
      emitter and there is still one source for what the project registered.
- [x] 2.2 Emit the nested-member description per design D3 in both emission modes
      (identical tree in each), preserving determinism and canonical ordering;
      apply the reserved-word escape identically to D4's runtime spelling.
- [x] 2.3 Unit tests: tree text pinned for the fixture shapes, escape spelling,
      byte-identical tree between strict and permissive, tree/overload identifier
      parity, and the empty-project root. Determinism across declaration orders is
      already covered for the whole stub text by the existing test, which now
      includes the tree — a second assertion of the same guarantee was dropped
      rather than duplicated.

## 3. Conformance at scale

- [x] 3.1 Regenerate the conformance fixture stub; extend `assertions.py` and
      `strict_assertions.py` with navigation claims: valid path yields the concrete
      type (all three shapes), invalid member is an error, degraded entry stays
      honest — read by mypy, pyright, and ty.
- [x] 3.2 Extend `hover_pyright.py` so the rendered hover for a navigated component
      matches the resolve() hover for the same component.
- [x] 3.3 Add the scale conformance leg per the spec's "scale does not change the
      outcome" scenario: a 2,000-entry tree verified by all three checkers.
      **Runs always, no opt-in** — measured at ~2s for all three combined, so the
      budget question the task anticipated did not arise and `.canon/checks.md`
      needs no new row (the Stub conformance row already covers it).

## 4. Size guard

- [x] 4.1 Implement the guard per design D5: documented 1,000-entry threshold
      constant with the evidence comment, report on identifier-narrowed emission
      past it (count, threshold, alternative), emission unchanged otherwise.
      Composed on `StubReport.oversized` so the core stays pure.
- [x] 4.2 Surface the report through the CLI adapter (stderr) without changing exit
      codes; unit tests for both spec scenarios including byte-identical output
      below the threshold.

## 5. Docs, surface, and validation

- [x] 5.1 Docs in the same change set (Rule 8): `get-editor-autocomplete.md` now
      teaches one grammar with two spellings, with a per-call-site comparison
      table, the always-strict property of the path, and the guard's meaning.
      The navigation demonstration is folded into the page's existing `main.py`
      rather than added as a second same-titled block — titled blocks are written
      by name into one project tree, so a duplicate would have silently replaced
      the original and stopped it running.
- [x] 5.2 Stability tier resolves by exposure — `apicheck` reports 0 fatal
      findings. `framework.objects` is a member of the already-public `Framework`,
      and `spoc.stubs.NARROWING_LIMIT` derives `public` from the package's
      `__all__`. The stability page enumerates packages, not exports, so it needs
      no edit.
- [x] 5.3 Run `task check` — full gate green including new conformance legs.
- [x] 5.4 Run `apidiff` and confirm the delta is additions only (minor-legal under
      the post-1.0 policy): `added: spoc.stubs.NARROWING_LIMIT (public)`, no
      breakage line attributable to this change.
- [x] 5.5 LSP rig promoted to `scripts/py/lab/completion_bench.py` (PEP 723 single
      file) and listed in `scripts/README.md`; design records why `lab/` and not
      `tools/`. Verified against the 50k tree workspace on first run.
