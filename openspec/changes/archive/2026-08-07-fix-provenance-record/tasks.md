## 1. Build-vs-adopt decisions — DONE

- [x] 1.1 `/ai:decide` has run. Two concerns, both approved and recorded in `DECISIONS.md`:
      **Origin record serialization — Adopt the standard library (`json`)** (supersedes the
      standing "TOML writing — not needed, dissolved by scope" ADR, whose premise this change
      invalidates) and **Origin record integrity — Build by construction**. See the verdict
      table in `design.md`.

## 2. Reproduce both defects first

- [x] 2.1 In `tests/test_scaffold_provenance.py`, add a failing test: generate from a template
      set whose manifest declares **no** origin record, and assert the generated project still
      contains the record naming the reference. It must fail on today's code.
- [x] 2.2 Add a failing test that a template set declaring a file targeting the reserved
      destination is refused before anything is written, with nothing at the destination.
- [x] 2.3 Add a failing test for the escaping defect the gate found: generate with a reference
      containing a backslash (`C:\templates\mine`) and a reference containing a quote, then
      assert `read_origin` returns those references **verbatim**. Both currently produce an
      unparseable record that `read_origin` reports as absent.

## 3. The scaffolder authors the record

- [x] 3.1 Change the record's format to JSON (D2): `RECORD_NAME` becomes `.spoc-template.json`,
      and `read_origin` parses with `json.loads`, keeping its existing contract that a malformed
      or partial record reads as absent rather than raising. Delete
      `src/spoc/scaffold/templates/default/spoc-template.toml.tmpl`.
- [x] 3.2 In `src/spoc/scaffold/provenance.py`, add the write side: build the record as a data
      structure from an `Origin` — including the `note` field carrying the explanation the old
      TOML comment header held — serialize it with `json.dumps`, and return the `PlannedFile`
      the operation appends. Keep it beside `read_origin` so writer and reader share one
      definition of the shape, and no format is assembled in program code.
- [x] 3.3 In `src/spoc/scaffold/operations.py`, have `init_project` build the `Origin` from the
      loaded set and append the record's `PlannedFile` to the plan **before** `sink.is_empty()`
      and `detect_conflicts` (D1, and the ordering risk the design calls out). `add_app` must
      not contribute the record.
- [x] 3.4 Remove `template_reference`, `template_revision`, and `template_set_name` from the
      `values` mapping in `init_project`, and from `values` in
      `src/spoc/scaffold/templates/default/manifest.toml` along with its `[[files]]` entry for
      the record.

## 4. Reserve the record's destination

- [x] 4.1 Add `ReservedTargetError` to `src/spoc/scaffold/errors.py`, naming the destination and
      stating it is reserved to the generating operation, in the house style ("Nothing was
      written").
- [x] 4.2 In `src/spoc/scaffold/core.py`, extend `validate_template_set` to refuse a set whose
      rendered destination is the reserved one, sourcing the name from `provenance.RECORD_NAME`
      rather than restating it (D3). Keep the check in the pure layer beside `_reject_escape`.
- [x] 4.3 Confirm the refusal is origin-independent — a built-in set claiming the destination
      fails exactly as a retrieved one does — and that `core.py` still imports nothing beyond
      the standard library and the kernel's identity grammar.

## 5. Remote failures name what the caller typed

- [x] 5.1 In `src/spoc/scaffold/remote.py`, thread the `Reference` into `_get` and raise
      `RetrievalError(reference.raw, …)`, carrying the derived location as reason detail rather
      than in place of the reference (D4). Cover every `_get` call site.
- [x] 5.2 Add a test asserting a failed `gh:owner/repo` retrieval names `gh:owner/repo`, not the
      `api.github.com` URL the adapter constructed.

## 6. Tests

- [x] 6.1 Make 2.1, 2.2, and 2.3 pass; keep the whole existing provenance suite green.
- [x] 6.2 Add a test that the record is emitted for a set obtained from outside the local system
      with content identical in shape to a built-in generation's, and that nothing the retrieved
      set carries appears in it.
- [x] 6.3 Add a test that a set still declaring the removed substitution values fails
      `UnsatisfiedValueError` before writing (the documented consequence of task 3.4).
- [x] 6.4 Add a test that `add_app` leaves the project's configuration byte-identical and does
      not rewrite the record.
- [x] 6.5 Check `tests/test_scaffold_parity.py` and `tests/test_scaffold_archive.py` still hold —
      the built-in set lost a file, so any test asserting its file count or manifest shape needs
      updating rather than deleting.

## 7. Docs (Rule 8, same change set)

- [x] 7.1 Correct `docs/docs/tools/cli.md:33` — the file is now `.spoc-template.json`, and the
      promise holds for every generated project, whatever the template set. Note that a project
      generated before this change carries an inert `.spoc-template.toml` that nothing reads.
- [x] 7.2 Update the template-set authoring docs: the reserved destination, and the removal of
      the three record-only substitution values from the vocabulary a set may declare.
- [x] 7.3 Update `docs/architecture/scaffold-resolution.md` if the plan's composition changed
      shape — the record now joins the plan outside the template-set rendering path (Rule 1).

## 8. Validate and close

- [x] 8.1 Run `task check` (or the `.canon/checks.md` rows individually) and report anything
      that could not be run as unverified.
- [x] 8.2 Verify end-to-end against the live fixture — **fully verified**, in two passes either
      side of the push (the fixture is this repo, so the remote half could only close once the
      change was on `origin/main`).

      Before the push:
      - `gh:hlop3z/spoc` resolved `HEAD` to `b55967ae…` (exactly `origin/main`), fetched,
        admitted, and retained the tarball. The remote path works.
      - That run then failed with `UnsatisfiedValueError` naming `template_reference`, writing
        nothing — the *published* set still declared the removed values. Task 6.3's behaviour,
        confirmed against real third-party-shaped content rather than a fixture.
      - A record-less set on a backslash-heavy Windows path produced `.spoc-template.json` with
        the reference round-tripped verbatim. Both defects fixed, end to end.

      After the push (`840e52f`):
      - `spoc init --template gh:hlop3z/spoc#subdirectory=…` generated a project whose record
        carries `revision = 840e52f5…`, matching `origin/main` exactly.
      - The generated project starts unedited: `Installed apps: ['apps.core']`, two components
        registered.
      - `spoc app billing` against the same origin reported **no divergence** — so the record a
        real remote generation wrote was read back and compared clean. The write side and the
        read side agree over a live reference, which is the whole point of the record.
- [x] 8.3 Review the diff and split into commits by intent (Rule 3): the conformance fix, the
      reserved-target hardening, the error-message fix, and the docs correction.
