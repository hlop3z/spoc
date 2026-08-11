# Keyword-Safe Decorator Names — Design

## Context

`decorator_names` in `src/spoc/scaffold/core.py` is the single place a declared kind
becomes a Python variable. Two files depend on the answer agreeing with itself: the
framework declaration binds `<name> = framework.kind("<kind>")`, and each generated app
module does `from framework import <name>`. That single-source property is why the fix has
one site.

Today the derivation is two stages:

1. `_singular(kind)` — conservative English singularization (`views` → `view`,
   `stories` → `story`, `middleware`/`status` untouched).
2. a fallback to the kind's own name when the singular is *unsafe*, where unsafe means
   any of: it duplicates another kind's singular, it equals another declared kind, or it
   is a Python keyword.

The third condition is the broken one. Falling back to the kind is a fine answer when the
keyword appeared during singularization — `ifs` → `if` → back to `ifs`. It is no answer at
all when the kind *is* the keyword: `class` → `class` → `class`, and the generated project
does not parse.

Note what is **not** wrong. The identity grammar accepts `class` as a kind segment and the
kernel registers `class:shop.example` without complaint. The per-kind module is written to
`apps/shop/class.py` and loaded through `importlib.import_module`, which imports
keyword-named modules perfectly well. Only two lines of generated *source text* are
illegal. So the defect lives at the point where a name crosses into Python syntax, and
nowhere earlier.

## Goals / Non-Goals

**Goals:**

- Every kind the identity grammar accepts generates a project that parses.
- One rule for keyword collisions, independent of which stage produced the collision.
- The derived names in a generated project are distinct, always.

**Non-Goals:**

- No restriction on kind names. Refusing `class` at validation would make the scaffolder
  stricter than the kernel it scaffolds for.
- No better singularization. `_singular` stays exactly as conservative as it is; the
  reasoning for that is unchanged and recorded in its docstring.
- No handling of shadowed *builtins* (`types` → `type`). A shadowed builtin is legal
  Python and a style matter in a file the author owns; a keyword is a parse error. Only
  the parse error is in scope.

## Decisions

### ADR-1 — Keyword escaping: Adopt the standard (PEP 8), not a library

- **Status**: approved
- **Why**: the concern reads as "turn a category name into a legal identifier", which
  sounds like an inflection problem and is not — the singularization half is already
  decided and deliberately conservative, and the half that is actually broken is answered
  by a convention Python itself publishes. PEP 8: *"single trailing underscore is used by
  convention to avoid conflicts with Python keyword, e.g. `class_`"*. The standard library
  applies it (`dataclasses.field(metadata=...)` neighbours, `typing.TypedDict`'s
  `class_getitem`, countless `id_`/`type_` parameters), and any reader who has met
  `class_` knows what it means without being told. Detection is `keyword.iskeyword`, from
  the standard library, already imported in this module — the authoritative list, updated
  with the language, that no local table could match. This is Rule 9 in its plainest form:
  adopt the global standard rather than invent a spelling.
- **Considered**:
  - **Adopt an inflection library** (`inflect`, `inflection`) — rejected on two counts.
    It solves the half that is not broken and does not solve the half that is: no
    inflection library escapes keywords. And it cannot be adopted at all — the
    distribution's `dependencies = []` is an invariant (`one-distribution` mandate), so a
    runtime dependency for a cosmetic naming nicety is not on the table.
  - **Refuse keyword kinds at validation** — rejected. `validate_name` delegates to the
    kernel's `validate_segment`; making the scaffolder reject a name the kernel accepts
    splits one grammar into two, and the error would tell an author their kind is illegal
    when it is not. The scaffolder's job is to emit legal Python for a legal kind.
  - **Prefix instead of suffix** (`kind_class`, `_class`) — rejected. Both are legal; both
    are inventions. A leading underscore additionally reads as "private" and would be
    excluded by `from framework import *` habits.
  - **Reword the decorator** (`class_kind`, `klass`) — rejected. `klass` is folklore, not
    a standard, and per-keyword rewording is an unbounded table.
- **Isolation**: `_escape_keyword` and `decorator_names` in `src/spoc/scaffold/core.py`.
  No template changes — the templates already interpolate `$decorator` and never spell a
  name themselves.

### ADR-2 — Distinctness is enforced after escaping, by appending underscores

- **Status**: approved
- **Why**: escaping can create a collision the pre-escape check cannot see. Kinds `class`
  and `class_` both arrive at `class_`, and `framework.py` would then bind one variable
  twice — the second binding wins, the first kind's app module imports the wrong
  decorator, and nothing raises. The existing pre-escape fallback stays (it produces the
  good `views`/`view` outcome), and a final pass appends underscores until each name is
  unused. It is total, it terminates, and it degrades in the only direction that keeps the
  file importable. The pathological input gets ugly names; every ordinary input is
  untouched, because with no collision the pass does nothing.
- **Considered**: raising an error on the collision (rejected — it would refuse a legal
  pair of kinds for a cosmetic reason, and the whole function's stance is that a working
  file beats a pretty variable); numbering the duplicates `class_2` (rejected — invents a
  scheme where extending the existing underscore convention already reads correctly).
- **Isolation**: the loop inside `decorator_names`. Order comes from the declared kinds
  tuple, so the result is deterministic.

## Risks / Trade-offs

- **`ifs` now yields `if_` where it used to yield `ifs`.** A behaviour change to generated
  output, accepted deliberately: one rule beats two outcomes that differed only by which
  stage happened to produce the keyword. Nothing in the repository or in a released
  template set depends on the old spelling, and generated projects are the author's from
  the moment they are written.
- **Underscore-suffixed variables are slightly less pretty.** They appear only where the
  language forces them, which is the same trade PEP 8 already made.
