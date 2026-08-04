## Why

The kernel reads exactly one file — `spoc.toml`, through stdlib `tomllib` — and that is
correct and stays. Everything past that boundary is currently the project author's problem,
and the problem is bigger than it looks. An app that carries a YAML fixture, a CSV lookup
table, and a JSON seed file writes three loaders, learns three parse conventions, and then
invents a fourth thing: a way to *address* into the result. Multiply by every app in the
project and the same forty lines get retyped with slightly different bugs each time.

The zero-dependency invariant makes it tempting to call this out of scope. But declining to
solve it does not remove the work — it distributes it, unversioned, into every downstream
project, which is exactly the outcome the canon's rebuild precedent (`loc` vs `tokei`) warns
about. Meanwhile the pieces that would solve it are all mature, standardized, and already
written: stdlib parsers for three of the five formats, a maintained library for the fourth,
and — since 2024 — two IETF RFCs covering the addressing problem that would otherwise be
hand-rolled as a dotted-key accessor.

What is missing is not a parser. It is one normalization contract and one place to put it.

## What Changes

- A **`spoc.formats` sidecar** that reads and writes JSON, TOML, YAML, XML, and CSV from both
  text and files, normalizing every one into a JSON-shaped mapping as the intermediate
  representation. `Any Format → JSON (IR) → Any Format`.
- **The kernel does not use it.** This is a surface for the developer, not a dependency of
  `start()`. `src/spoc/core/config.py` is untouched, and the kernel imports nothing from
  `spoc.formats` — the same one-way contract `spoc.scaffold` already satisfies and a test
  already asserts.
- **Optional extras appear for the first time in this distribution.** JSON, CSV, and
  TOML-reading are standard library and cost nothing. YAML, XML, and TOML-*writing* are
  quarantined behind `spoc[yaml]`, `spoc[xml]`, `spoc[toml]`, and `spoc[full]`. A format whose
  extra is absent fails at the boundary naming the extra to install — never at import, and
  never as an `ImportError` from a transitive module.
- **Collection, not just loading.** A directory of mixed-format files resolves to one mapping
  in a single call, so a project stops hand-loading file by file. This is the original
  motivation and the part that does not exist off the shelf.
- **Loading is eager. Deliberately.** A lazy variant was explored and rejected: it moves parse
  errors from one predictable point to whichever code path first touches the key, makes
  `.keys()` lie unless discovery stays eager anyway, and buys nothing once the loader is
  developer-invoked rather than wired into boot.
- **Access is two adopted standards, not one invented one.** Exact addressing uses **JSON
  Pointer (RFC 6901)**, which resolves to exactly one value and fails loudly on a typo. Querying
  uses **JSONPath (RFC 9535)**, which returns a nodelist and may legitimately be empty. The
  split is by job: configuration reads must fail loudly, dataset queries must not.
- **XML normalizes to the map shape with declared list paths.** The alternative — a
  hyperscript/JsonML tree, `h(tag, attrs, children)` — is lossless and needs no declaration, but
  is unusable as configuration without a second projection layer on top. Cardinality genuinely
  is not derivable from an instance document, so declaring it is supplying missing information
  rather than restating derivable information.

## Capabilities

### New Capabilities

- `format-codecs`: the normalization contract — which formats are supported in which
  directions, what the JSON IR guarantees, how XML and CSV map onto it, and how an absent
  optional extra fails.
- `data-collection`: resolving a tree of mixed-format files into one addressable mapping —
  how entries are keyed, how collisions are refused, and what eager loading guarantees.
- `data-access`: addressing into the IR — RFC 6901 for exact reads, RFC 9535 for queries, and
  the failure semantics that distinguish them.

### Modified Capabilities

None. The kernel's observable behavior is unchanged in every particular: configuration
loading, discovery, identity, and resolution do not move, and `spoc.toml` continues to be read
by `tomllib` alone. That this change is purely additive is load-bearing — if the developer
data surface required a kernel change, the kernel's boundaries would be wrong.

## Impact

- **Critical concerns** — four, gated through `/ai:decide` before any code and recorded as ADRs
  in `design.md` D6. Three landed on Adopt (`xmltodict` for XML, `python-jsonpath` for both
  access standards, `ruamel.yaml` for YAML) and one on a justified thin Build: the loader and
  collection layer, because adopting `anyconfig` or `dynaconf` would make either a dependency of
  every format including JSON, breaking this change's own bare-install requirement.
- **Distribution**: `[project.optional-dependencies]` is added to `pyproject.toml`.
  `dependencies = []` stays literally unchanged, and installing `spoc` bare acquires nothing.
- **Kernel**: no change to `src/spoc/core/` or `src/spoc/framework.py`.
- **Registry**: no automatic integration. Registering collected data as a `data:` kind under
  the existing `kind:namespace.object_name` grammar is attractive and is recorded as an open
  question, not built — it would be an opt-in helper the developer's own `Framework(...)`
  declaration drives, never something the kernel initiates.
- **Docs**: a new guide page; the architecture diagram gains a sidecar box that touches nothing
  inward (Rule 1).
- **Size**: this is net-additive against a standing LOC-reduction mandate. The mitigation is
  that every concern in D6 that lands on "adopt" costs approximately zero lines of this
  project's code, and the adopted access standards *delete* the dotted-key accessor the
  original sketch would have required.
