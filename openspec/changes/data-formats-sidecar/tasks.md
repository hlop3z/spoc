## 1. Gates before any code

- [x] 1.1 Run `/ai:decide` for the four concerns in design.md D6 — decided: loading and
      collection Build-thin over adopted parsers, XML `xmltodict`, access `python-jsonpath`,
      YAML `ruamel.yaml`
- [x] 1.2 If D6 lands mostly on "build" rather than "adopt", cut scope before proceeding — not
      triggered: three of four concerns landed on Adopt, and the one Build is thin orchestration
      over adopted parsers with no parsing of its own
- [x] 1.3 Resolve design.md Open Questions 2 and 3 (collection key derivation, extra naming) into
      the specs; leave Open Question 1 (registry `data:` kind) deferred and out of scope —
      resolved as D8 (dot-joined path segments under the kernel's identity grammar) and D9
      (`yaml`/`xml`/`toml`/`full`)
- [x] 1.4 Spike the XML round trip on a namespaced document with mixed content and comments, to
      confirm the stated lossy limits in `format-codecs` are the real ones before they are
      written into docs — findings recorded in design.md D3; namespaces are lossless, mixed
      content merges text rather than only reordering it

## 2. Package boundary

- [x] 2.1 Create `src/spoc/formats/` as a sidecar package on the `spoc.scaffold` contract
- [x] 2.2 Extend the existing one-way dependency test to assert the kernel imports nothing from
      `spoc.formats`, and that importing `spoc` loads no optional dependency
- [x] 2.3 Add `[project.optional-dependencies]` to `pyproject.toml` with the per-format extras and
      an aggregate extra; assert `dependencies = []` is unchanged
- [x] 2.4 Add a test that runs the standard-library formats in an environment with no optional
      dependency installed

## 3. Core — the representation and the codec port

- [x] 3.1 Define the `Codec` port: decode text to representation, encode representation to text,
      with read and write support declared independently per format (D2)
- [x] 3.2 Implement the codec registry keyed by format name and file extension, resolving
      factories lazily so import loads nothing optional
- [x] 3.3 Implement missing-extra failure that names the extra to install, tested by simulating
      absence rather than by inspecting the message in place
- [x] 3.4 Implement the enumeration of supported formats and their currently available directions
- [x] 3.5 Assert by test that the core module imports nothing outside the standard library

## 4. Codecs

- [x] 4.1 JSON codec — read and write, standard library
- [x] 4.2 Tabular codec — read and write, standard library, minimal-mode record mapping
- [x] 4.3 TOML codec — read on the standard library; writing behind its extra, declared as a
      separate direction rather than a special case
- [x] 4.4 YAML codec on `ruamel.yaml` behind its extra, restricted to safe loading
- [x] 4.5 XML codec on `xmltodict` behind its extra, with caller-declared repeating paths driven
      through `force_list`'s callable form — the tag-name form cannot express per-path
      cardinality (D3, D6)
- [x] 4.6 Round-trip test per writable format, and cross-format conversion tests over the
      representation

## 5. Collection

- [x] 5.1 Implement directory walk with extension-based format resolution and a reportable
      skipped set
- [x] 5.2 Implement key derivation from the path relative to the collection root, extension
      removed (per 1.3)
- [x] 5.3 Implement collision refusal naming both conflicting paths, with no precedence or merge
      fallback
- [x] 5.4 Implement eager parsing with whole-collection failure — no partial mapping returned on
      any file's parse failure
- [x] 5.5 Test that enumeration is truthful: keys present are exactly the values loaded

## 6. Access

- [x] 6.1 Implement exact addressing per RFC 6901, failing with the unresolvable segment named
- [x] 6.2 Implement querying per RFC 9535, returning a possibly-empty result set
- [x] 6.3 Pin `python-jsonpath`'s RFC-strict entry points and prove RFC 9535 conformance against
      the JSONPath Compliance Test Suite — the package is a deliberate superset, so its default
      surface is not the standard (design.md D6, risk accepted). If strict mode is unavailable,
      fall back to `jsonpath-rfc9535` plus a separate pointer library rather than shipping a
      dialect — **strict mode reached**; every non-RFC extension is rejected. See D10 for the
      trap found along the way, and 6.4 for what conformance was and was not proven against
- [x] 6.4 State explicitly any portion of the standard not supported — none is knowingly
      unsupported: `iregexp-check` was added to the `query` extra so RFC 9535's own `match()`
      and `search()` work. **Unverified (Rule 6):** the full JSONPath Compliance Test Suite was
      not executed here — it is not vendored in the wheel, and the upstream package runs it in
      its own CI. What this repo asserts is the conformant/non-conformant behavior in
      `tests/test_formats.py`
- [x] 6.5 Test that absent and null are distinguishable through exact addressing
- [x] 6.6 Test both modes over values from every supported format and from a collection, to prove
      uniformity

## 7. Docs and validation

- [x] 7.1 Add the guide page: the five formats, the representation, collection, and the
      Pointer-vs-Path choice framed by failure semantics — `docs/docs/advanced/data-formats.md`,
      wired into the mkdocs nav
- [x] 7.2 Document the hierarchical markup limits — ordering, comments, mixed content — as
      declared limits, with the D3 reversal trigger stated
- [x] 7.3 Update the architecture diagram to show the sidecar with no inward edge (Rule 1) —
      also corrected invariant 1, which claimed the wheel declares no `Requires-Dist` at all;
      extras appear there as conditional entries a bare install never resolves
- [x] 7.4 Run `.canon/checks.md`; report anything unrunnable as unverified (Rule 6)
- [ ] 7.5 Fold the D6 ADRs into `DECISIONS.md` on archive
