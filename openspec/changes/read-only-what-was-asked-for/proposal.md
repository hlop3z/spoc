## Why

Two read paths traverse the whole of something in order to hand back a part of it. A
collection walks every entry under its root — descending the tool directories it has
already decided to skip — and only then discards them; a registry listing narrowed to one
kind walks every registered component and filters. In both cases the cost is set by the
size of what was *not* asked for, which is the size that grows without bound: a repository's
`.git`, a framework's whole registry.

Neither is a hypothetical. `.git`, `.venv`, and `node_modules` are exactly the directories a
data tree sits beside, and they are the ones a collection stats every entry of before
throwing them away. And the registry already answers a per-facet read directly — the
listing surface is the one caller that does not ask it to.

## What Changes

- A collection decides whether to descend a directory **before** descending it. An entry
  whose name is hidden or matches an ignore pattern is skipped as a unit, and nothing
  beneath it is enumerated, stat'ed, or considered.
- **BREAKING** (report shape, not API): the reportable skipped set names the **skipped
  directory** rather than each file beneath it. This is what the hidden-entry scenario
  already specifies ("the directory appears in the reportable skipped set") and what the
  current implementation does not do — it reports only files, so a skipped directory never
  appears under its own name and an ignored tree contributes one entry per file it holds.
- The registry listing operation, when narrowed to a kind, reads that kind's facet instead
  of enumerating every record and filtering. Ordering is taken from the read rather than
  re-established by the caller.
- No signature changes. `collect` and the list operation keep their parameters, their
  return types, and every guarantee about what they collect and report.

## Capabilities

### New Capabilities

None. Both changes tighten cost and reporting guarantees on capabilities that already
exist.

### Modified Capabilities

- `data-collection`: the skip requirement gains a traversal guarantee — a skipped
  directory is not descended, and the skipped set names the skipped entry itself rather
  than its contents. The scenario for explicit ignore patterns changes what it asserts
  appears in the skipped set.
- `project-diagnostics`: the list requirement gains a cost guarantee — narrowing to a kind
  costs that kind rather than the whole registry.
- `component-registry`: no requirement changes, but the facet-read contract it already
  states is what the diagnostics change consumes. Listed here only if review finds the
  guarantee needs stating from the reader's side; the default is to leave it untouched.

## Impact

- `src/spoc/formats/operations.py` — `collect` and `_is_ignored`.
- `src/spoc/diagnostics/core.py` — `list_records`.
- `tests/test_formats.py` — `test_ignore_patterns_extend_the_skip_set` asserts a file path
  in the skipped set and must assert the directory instead. Two neighbouring skip tests use
  substring matching and stay green as written.
- No dependency, CLI-argument, or public-signature change. `spoc list` output is unchanged;
  only what it costs to produce changes.
- The `Collection.skipped` field is public surface, so the report-shape change is a
  surface-behavior change even though the type is the same.
