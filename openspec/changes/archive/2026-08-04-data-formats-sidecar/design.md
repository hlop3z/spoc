## Context

Three constraints shape everything below:

1. **`dependencies = []` is an invariant of the published package.** Every dependency this
   change acquires must reach only the developer who asks for it by extra.
2. **The kernel must not gain a dependency on this surface.** `spoc.scaffold` already
   established the contract — ships in the distribution, imported by nothing inward, deletable
   without touching the kernel — and this change reuses it rather than inventing a second
   arrangement.
3. **Almost all of this is solved elsewhere.** The rebuild precedent (`loc` vs `tokei`) applies
   with unusual force here, because the thing being described — "any format to a dict and back"
   — is the literal one-line description of at least two mature packages.

**Two candidate designs were explored and one was rejected.** The XML representation could be a
hyperscript tree — `h(tag, attrs, children)`, which is JsonML with constructor syntax instead of
array syntax, and which is what JSX compiles to. It is genuinely better on the merits that matter
to a *document*: children is always a list (so the cardinality declaration disappears), text
nodes are just strings in that list (so ElementTree's `.text`/`.tail` split disappears), and
construction and parsing share one shape. It was rejected because SPOC's XML is
configuration-shaped, and a tree is unusable as configuration without a second map-projection
layer built on top of it — which is more of this project's code, against a standing reduction
mandate, to serve a document case that has not appeared. The trade is recorded in D3 and the
reversal trigger is named there.

## Goals / Non-Goals

**Goals:**

- One call reads any supported format from text or a file into a JSON-shaped mapping.
- One call collects a directory of mixed formats into a single mapping.
- Addressing into the result uses adopted standards, not a bespoke accessor.
- A bare `spoc` install acquires nothing; a missing extra fails by naming itself.
- The surface is deletable — removing `spoc/formats/` leaves the kernel and its suite intact.

**Non-Goals:**

- **Not a kernel dependency.** `start()` does not call it; `config.py` does not change.
- **Not lazy.** See D4.
- **Not a schema/validation framework.** Normalizing and addressing only. Validation is a
  separate concern with separate mature answers (Rule 9 names JSON Schema); if it is wanted it
  is its own proposal.
- **Not automatic registry integration.** See Open Questions 1.
- **Not a CLI.** Format conversion at the command line is `dasel`'s job, which already covers
  exactly these five formats. If a workshop need arises it is an `ensure` entry, not code here.
- Not a streaming or out-of-core loader. Files that do not fit in memory are out of scope.

## Decisions

### D1 — The IR is a JSON value, and that is the whole contract

Every codec produces, and accepts, values drawn from the JSON data model: object, array,
string, number, boolean, null. Nothing else crosses the boundary — no format-specific node
types, no library objects, no `datetime` unless a codec is explicitly documented to widen it.

This is what makes the rest composable. Because the IR *is* JSON, the access standards in D5
apply uniformly to a TOML table, a CSV table, and an XML document with no per-format
adaptation, and the IR's own shape is expressible in JSON Schema if it ever needs publishing
(Rule 9).

### D2 — Codecs are adapters behind a registry keyed by format, resolved lazily

The core holds a `Codec` port — decode text to IR, encode IR to text — and a registry mapping
format name and file extension to a codec factory. Factories are invoked on first use, so
importing `spoc.formats` never imports PyYAML or xmltodict.

A codec whose optional dependency is absent MUST fail with a message naming the extra
(`pip install spoc[yaml]`) at *resolution* time. It must never surface as a raw `ImportError`
from a transitive module, and it must never fail at import of `spoc.formats` itself — otherwise
the extras are not optional in practice.

Direction is a property of the codec, not an assumption. Stdlib `tomllib` reads and cannot
write; that asymmetry is declared data on the codec, so "TOML output needs `spoc[toml]`" is a
lookup rather than a special case in calling code.

### D3 — XML normalizes to the map shape, with list paths declared

XML decodes to nested mappings with attributes and text distinguished by prefix convention,
not to a tree of uniform nodes. Repetition is resolved by **declared paths** — `catalog.book` —
supplied by the caller, not by counting occurrences in the instance document.

The declaration is not a violation of "never make the developer restate what the kernel can
derive." Cardinality is schema information; a document containing one `<book>` is genuinely
ambiguous between "the only one" and "one of many", and an instance document carries the bit
nowhere. Deriving it from occurrence counts is the well-known failure that breaks on
single-row data. Asking is supplying missing input, not restating derivable input.

Paths rather than bare tag names, because the same tag at different depths can have different
cardinality and a name-keyed declaration cannot express that.

**Reversal trigger**: the first genuine document-shaped XML requirement — mixed content, or
significant element ordering, or a need to *construct* XML precisely rather than round-trip a
map. At that point the hyperscript IR from Context is the answer and this decision is reopened
honestly, rather than patching the map shape to half-carry ordering.

**Spike findings (tasks.md 1.4).** Run against `xmltodict` 1.0.4 on a namespaced document with
mixed content and a comment. Four results changed what gets documented:

- **Declared repeating paths work as designed.** `force_list`'s callable receives
  `(path, key, value)` where `path` is a tuple of `(name, attrs)` ancestor pairs. The addressable
  path is therefore `names(path)[1:] + (key,)` — *relative to the document root element, which is
  excluded*. A one-element document and a many-element document both yield an array at a declared
  path, confirming the shape does not follow the data.
- **Mixed content is worse than "ordering is lost" — text is merged.**
  `<desc>Hello <b>world</b>!</desc>` reads as `{"b": "world", "#text": "Hello !"}`: the two text
  fragments are concatenated and their position relative to the child element is gone. Task 7.2
  must say merged, not just reordered.
- **Comments are dropped silently**, as assumed.
- **Namespaces survive intact**, which was *not* assumed. In the default mode
  (`process_namespaces=False`) prefixes are preserved verbatim as key text (`dc:title`) and
  reproduced exactly on write. So namespaces stay out of the declared lossy set, and the codec
  keeps that default. Enabling namespace processing would restructure `xmlns` declarations into
  a nested map and lose that property.
- **The round-trip requirement in `format-codecs` is satisfiable despite the above.** Read →
  write → read is equal at the value level and idempotent from the second generation on, which is
  what the spec asks for — it requires re-read equality, not byte fidelity.

### D4 — Loading is eager; the lazy variant is rejected

A load call parses fully before returning, and a collection call parses every file it collected.

Lazy parsing was explored on the strength of "do not pay for data you never touch." It loses:
a parse error surfaces at whichever call site first reads the key rather than at one
predictable point, so a typo in a rarely-read file ships; and `.keys()`/`in` are wrong unless
discovery stays eager anyway, which means the deferral only ever covers parsing, not scanning.
Both objections could be bought off with a `verify()` escape hatch and eager discovery — which
is machinery, in this project's code, to reconstruct the behavior eager loading has for free.

The decision is easier than it would have been, because this surface is developer-invoked
rather than wired into `start()`. There is no boot to defer work out of.

### D5 — Two access standards, split by failure semantics

- **RFC 6901 (JSON Pointer)** for exact addressing — `/server/port`. Resolves to exactly one
  value or raises, naming the segment that failed.
- **RFC 9535 (JSONPath)** for queries — `$.users[?@.active == true].email`. Returns a nodelist,
  possibly empty, and an empty result is a valid answer rather than an error.

The split is the point. RFC 9535 defines no-match as an empty nodelist, never an error, so a
typo'd `$.serverr.port` silently reads as absent — a direct regression against the precision
`registry.py` is built around ("fails per segment… rather than as a blanket not-found").
Pointer restores loud failure for the case that needs it. Configuration reads are exact and
must fail loudly; dataset queries are filters and must not.

Naming RFC 9535 specifically, rather than "JSONPath", is deliberate: the pre-2024 landscape was
a 2007 blog post and twenty incompatible interpretations, and the RFC exists to end that.
Conformance against the JSONPath Compliance Test Suite is therefore an adoption criterion in
D6, not a nice-to-have.

### D6 — Build-vs-adopt outcomes

**Status: decided.** Resolved through `/ai:decide`. Three of the four concerns fall under the
canon's never-hand-roll list (standard-format parsing and serialization), so for those the gate
decided *which tool*, never *whether to build*. The findings that drove the outcomes:

- **The bare-install requirement settles the loader question.** `format-codecs` requires that
  standard-library formats remain usable with no optional dependency installed. Adopting
  `anyconfig` or `dynaconf` makes that package a dependency of *every* format including JSON, so
  a bare `pip install spoc` could no longer read JSON. This is a conflict with an approved spec
  requirement, not a preference. `dynaconf` additionally re-owns environment layering, which
  `_MODE_CASCADE` already implements.
- `xmltodict` 1.0.4 (February 2026, MIT, pure Python, no dependencies, Python 3.9–3.14)
  implements the D3 shape. Decisively, its `force_list` accepts a **callable** receiving
  `(path, key, value)`, which is exactly the hook D3's declared repeating *paths* require — the
  tag-name form alone could not express per-path cardinality. `unparse` supplies the write
  direction. `xmljson` implements all six named conventions but is unmaintained and its own
  documentation redirects to `xmltodict` — a hard reject on maintenance.
- There is no de-jure XML-to-JSON standard, deliberately — W3C standardized the opposite
  direction (`fn:json-to-xml`) because the mapping is lossy on attributes, namespaces, ordering
  and mixed content. D3's convention is therefore necessarily a de-facto adoption.
- For CSV, `csv2json` (W3C Recommendation, 2015) *is* the de-jure standard, and its **minimal
  mode** output is an array of one object per row — which stdlib `csv.DictReader` already
  produces. Standards alignment is free; CSVW's standard mode with a JSON-LD descriptor is the
  named upgrade path if typed columns are ever needed.
- `python-jsonpath` 2.2.1 (July 2026, MIT, no third-party dependencies) ships RFC 9535, RFC 6901
  and RFC 6902 in one package, so both D5 standards arrive as a single dependency.
  `jsonpath-ng` predates the RFC and implements a pre-standard dialect — rejected before the
  gate on those grounds.
- **YAML forced a trade between correctness and governance.** PyYAML implements YAML **1.1**,
  whose implicit booleans parse `NO` as `False` (the Norway problem) and whose sexagesimal rule
  parses `12:30` as `750`. `ruamel.yaml` implements YAML **1.2**, a strict JSON superset, and
  dropped its C-library dependency in 0.19.1. But ruamel is single-maintainer on SourceForge
  Mercurial, and the Ansible community forked it as `ruyaml` explicitly "to secure the future of
  the library, mainly by having a pool of maintainers." Against that, its adoption is
  unambiguously enterprise-grade: aws-cli v2, ansible-lint, mitmproxy, conda, esphome,
  jupyterlab-server, check-jsonschema, and ~0.5M downloads per day.

#### Decision: Multi-format loading and collection — Build (thin) over adopted parsers

- **Status**: approved
- **Why**: Adopting `anyconfig` would make it a dependency of every format including JSON,
  breaking the bare-install requirement `format-codecs` already states. What remains to build is
  a dispatch table, a directory walk, key derivation, and collision refusal — none of which is
  standard-format parsing, and every parser underneath it is adopted.
- **Considered**: adopt `anyconfig` (covers ~90% of the codec layer, but the bare-install
  conflict is fatal and its query layer is jmespath, so RFC 9535 would still be a second
  dependency); adopt `dynaconf` (same conflict, plus it duplicates `_MODE_CASCADE` and is a
  settings framework rather than a codec layer).
- **Isolation**: the `Codec` port (D2). Calling code sees the port, never a codec.

#### Decision: XML dict convention — Adopt `xmltodict`

- **Status**: approved
- **Why**: Maintained (1.0.4, February 2026), MIT, pure Python with no dependencies, and its
  `force_list` callable form is the precise extension point D3's declared repeating paths need.
  `unparse` covers the write direction without a second library.
- **Considered**: build over stdlib `ElementTree` (zero dependencies and `Element` is close to
  the right shape, but it is hand-rolling standard-format parsing against the canon, and
  `.text`/`.tail` mixed-content handling is where it would go wrong); adopt `xmljson` for a
  named convention (unmaintained — hard reject).
- **Isolation**: one codec adapter, which owns the path-matching predicate handed to
  `force_list`.

#### Decision: JSON Pointer and JSONPath engine — Adopt `python-jsonpath`

- **Status**: approved
- **Why**: One MIT dependency with no third-party requirements covers both D5 standards —
  RFC 6901 for exact addressing and RFC 9535 for querying — where the alternative needs two.
- **Considered**: adopt `jsonpath-rfc9535` plus a separate pointer library (strict conformance
  with no superset ambiguity, at the cost of a second dependency); adopt `jsonpath-ng` (rejected
  on dialect grounds before the gate).
- **Criterion**: passes the JSONPath Compliance Test Suite (D5).
- **Risk accepted**: `python-jsonpath` is a deliberate *superset* of RFC 9535 — its
  strict-conformance sibling exists for that reason. Task 6.3 must pin the RFC-strict entry
  points and prove conformance, or the `data-access` requirement is unmet. If strict mode proves
  unavailable, the fallback is the two-dependency option above.
- **Isolation**: an access module that no codec imports.

#### Decision: YAML parser — Adopt `ruamel.yaml`

- **Status**: approved
- **Why**: YAML 1.2 is a strict JSON superset, which matches D1's "the IR is a JSON value"
  contract exactly rather than approximating it, and it avoids the Norway problem by
  specification rather than by patching. Maturity and enterprise adoption were tested explicitly
  and pass: aws-cli v2, ansible-lint, mitmproxy, conda, ~0.5M downloads/day.
- **Considered**: adopt `PyYAML` as-is (better governance — multi-maintainer, on GitHub,
  ubiquitous — but inherits YAML 1.1's implicit-boolean and sexagesimal footguns knowingly);
  extend `PyYAML` by narrowing its bool resolver (~5 lines, keeps PyYAML's governance and kills
  the headline footgun, but leaves SPOC speaking a third dialect that disagrees with every other
  PyYAML-based tool, and the quieter 1.1 quirks remain).
- **Risk accepted**: single maintainer, hosted on SourceForge Mercurial, with a community fork
  (`ruyaml`) existing because upstream is hard to contribute to. Bounded two ways: the `Codec`
  port makes a backend swap a one-adapter change, and `ruyaml` is a drop-in replacement if
  upstream stalls.
- **Isolation**: one codec adapter, restricted to safe loading.

### D7 — Ships in the main distribution, behind extras

`spoc.formats` ships alongside `spoc.scaffold` in the same distribution. The kernel imports
nothing from it, asserted by the same test that already asserts the scaffolder's one-way
dependency. Extras quarantine every acquired package, so `pip install spoc` is unchanged and
`pip install spoc[full]` is the opt-in.

### D8 — Collection keys are dot-joined path segments under the kernel's own grammar

An entry's key is its path relative to the collection root, extension removed, with the
separators replaced by dots: `data/blog/posts.yaml` → `blog.posts`. Every segment MUST satisfy
the kernel's existing identity grammar (`^[a-z][a-z0-9_]*$`), validated through
`core.identity.validate_segment` rather than a second pattern defined here (Rule 7).

Dots rather than slashes, because that is already the grammar's separator between namespace and
object name. A key produced this way is directly usable as the `namespace.object_name` tail of a
canonical identifier, which is what keeps Open Question 1 reachable without redesigning keys
later. Slash-separated keys would have needed translating at that boundary.

Reusing the grammar also disposes of the ambiguity a dotted filename would introduce:
`my.data.yaml` does not silently become the two-segment key `my.data`, it is rejected by
`validate_segment` naming the offending value — the same failure a bad component name gets.

### D9 — The aggregate extra is named `full`

Per-format extras are `yaml`, `xml`, and `toml`; the aggregate is `full`. Chosen over `all`
because it is the term this change was framed in from the outset, and because a downstream
framework's own `all` is more likely to collide conceptually than a `full` that reads as
"the whole of spoc's optional format support".

### D10 — RFC 9535 strictness is reached by sentinel tokens, never by blanking them

`python-jsonpath`'s default environment is already *conformant* — including the subtlety that a
bare relative query in a filter is an existence test, not a truthiness test. What it will not do
is **reject** its own extensions, so a query using the keys selector, a union, an intersection,
or the pseudo-root would work here and fail on every other RFC 9535 engine. Shipping that is
shipping a dialect.

The environment therefore rebinds each extension token to `"\x00"`, a character that cannot
occur in a source string.

**The trap:** blanking those tokens to `""` looks equivalent and is not. An empty
`keys_selector_token` makes the lexer misparse *conformant* filters — `$.users[?@.active]`
silently returned `[]` instead of its two matches, and a comparison filter raised a type error.
That failure is silent and wrong-answer-shaped, which is the worst kind. The sentinel keeps the
lexer intact while making every extension unreachable, and `tests/test_formats.py` asserts both
halves: six conformant forms produce RFC-correct results, four extensions raise.

A consequence worth noting: `iregexp-check` joined the `query` extra. Without it the RFC's own
`match()` and `search()` functions are unavailable, so conformance would have been partial in a
way nothing in the code would have said out loud.

## Risks / Trade-offs

- **This is net-additive against a LOC-reduction mandate.** → Accepted, and bounded by D6: every
  concern that lands on "adopt" costs approximately zero lines here, and D5's standards delete
  the dotted-key accessor the original sketch required. If D6 lands mostly on "build", that is
  the signal to cut scope rather than to proceed.
- **"Extra things the developer might need" is how a kitchen sink starts.** → The Non-Goals list
  is the stopping rule, and it is deliberately long. A new format or a new access idiom is a new
  proposal, not an addition here.
- **Optional extras are a new failure surface for users.** A missing extra is a confusing error
  if it leaks as `ImportError`. → D2 makes naming the extra a spec requirement, tested by
  simulating absence rather than by inspection.
- **The XML map shape is lossy.** Ordering, comments, and mixed content do not survive. →
  Accepted and documented as a stated limit rather than a bug, with the D3 reversal trigger
  naming what would change the decision.
- **Collection keys could collide** across formats — `settings.toml` and `settings.yaml` in one
  directory. → Specified as a refusal naming both paths, not a precedence rule; a silent winner
  is the worse failure.

## Open Questions

1. **Should collected data be registerable into the kernel registry as a `data:` kind?** It fits
   Rule 11's one grammar exactly — `data:blog.users` resolving to a document, then RFC 6901
   navigating its interior — and dependencies would still point inward, since `spoc.formats`
   would consume the registry's public API while the registry stays ignorant of it. Deferred
   because it is separable and this change is already the larger one. Not built here.
2. ~~Does collection key by relative path, by stem, or by a declared mapping?~~ **Resolved —
   D8.** Dot-joined relative path segments, extension removed, each validated against the
   kernel's identity grammar.
3. ~~Is `spoc[full]` the right name for the everything extra?~~ **Resolved — D9.** Yes;
   per-format extras alongside it are `yaml`, `xml`, `toml`.
