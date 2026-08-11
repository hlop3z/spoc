## Why

`spoc init shop --kinds class` generates a project that does not parse. The framework
declaration emits `class = framework.kind("class")` and the app module emits
`from framework import class` — two `SyntaxError`s in a project whose governing
requirement is that it "MUST produce a complete project that starts successfully without
any edit to the generated content".

The derivation already knows about keywords, but its only remedy is to fall back to the
kind's own name. That works when the *singular* is the keyword (`ifs` → `if` → back to
`ifs`) and fails completely when the *kind itself* is one, because the fallback lands on
the same illegal token it was escaping from. Nothing rejects the kind either: `class`
satisfies the identity grammar (`^[a-z][a-z0-9_]*$`) and the kernel registers it happily —
it is only the generated Python that breaks, so refusing the kind would impose a
scaffolder restriction on a name the kernel accepts.

The same gap produces a second, quieter inconsistency: two kinds whose derived names
collide only *after* escaping (`class` and `class_`) would bind one variable twice in
`framework.py`, and the second binding silently wins — the first kind's components would
register under the wrong kind with no error anywhere.

## What Changes

- The decorator-name derivation gains a final escaping step: a name a Python keyword owns
  is spelled with a single trailing underscore — PEP 8's own convention for exactly this
  collision (`class` → `class_`).
- **Behaviour change**: escaping now applies to the singular too, so `ifs` yields `if_`
  rather than falling back to `ifs`. One rule replaces two different outcomes that
  depended on where the keyword came from.
- Names are made distinct after escaping, not only before it, so no two kinds can bind the
  same variable in the generated declaration.
- Kind names remain unrestricted: any name the identity grammar accepts stays generatable.
  The escaping happens where the Python identifier is produced, not where the kind is
  validated.

## Capabilities

### New Capabilities

None. This closes a hole in a requirement that already exists.

### Modified Capabilities

- `project-scaffolding`: the "Generating a runnable project" requirement gains a scenario
  pinning the keyword case. The requirement already says the generated project must start
  unedited; it never said what that means for a kind whose name the target language
  reserves, which is why the case could be missed.

## Impact

**Affected code** — `decorator_names` and its helpers in `src/spoc/scaffold/core.py`.
Nothing else derives the name; that single-source property is what the change relies on.

**Affected tests** — `tests/test_scaffold.py::test_decorator_falls_back_to_the_kind_when_singular_is_unsafe`
asserts the old `ifs` → `ifs` outcome and must be updated, not merely extended.

**Affected documentation** — `docs/docs/learn/framework.md` states the singular rule in
prose; it must state the escape alongside it (Rule 8).

**Not affected** — the identity grammar, the kernel's registry, the per-kind module
filenames (`apps/x/class.py` imports fine through `importlib.import_module`), the starter
template set (fully concrete, no `--kinds`), and the dependency footprint, which stays
empty.

**Critical concerns** — one: how a category name becomes a legal Python identifier. It
looks like a job for an inflection library, and is not; `/ai:decide` records why in
`design.md`.
