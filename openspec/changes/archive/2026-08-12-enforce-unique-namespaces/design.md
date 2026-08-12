## Context

Two places derive a namespace, and neither records who claimed it.

`Framework._register_apps` takes each `[spoc.apps]` entry and uses
`app.rpartition(".")[2]` — the final path segment. `Framework._register_plugins` takes each
`[spoc.plugins]` reference and uses `segments[-2]` — the package holding the module. Both
call `validate_segment("namespace", …)`, so a malformed segment is caught; a *contested*
one is not.

Measured on the current build: declaring `["apps.shop", "vendor.shop"]` where both declare
`Product` raises `Duplicate identifier 'models:shop.product'`, which names neither package.
Change one to declare `Order` instead and both register cleanly into namespace `shop` with
no diagnostic at all. The second case is the one that matters — it produces a working
system whose identifiers lie.

Nesting is not exotic. `openspec/specs/project-configuration/spec.md` already specifies
`myproject.apps.blog → blog` and a plugin under `apps.blog.extras` taking `blog`. The
container-package layout is the specified, expected shape, and it is precisely the shape
that makes leaf collisions likely.

## Goals / Non-Goals

**Goals:**

- One namespace, one owning package — enforced at start, before any component registers.
- A collision reports the namespace and both claimants, in terms of the declaration.
- A collision is resolvable without renaming a package, since the colliding package may be
  vendored or third-party.
- The common case stays untouched: no entry gains required syntax.
- Both derivation sites obey one rule, checked in one place.

**Non-Goals:**

- Namespacing the namespace (hierarchical or dotted namespaces). The grammar is
  `kind:namespace.object_name` with single-segment namespaces, and Rule 11 fixes that.
- Auto-disambiguation. Deriving `vendor_shop` from `vendor.shop` on collision would make
  identifiers depend on which other apps happen to be installed — a component's identity
  must not change because a neighbour appeared.
- Reserving namespaces ahead of time, or a namespace registry separate from the app list.
- Cross-project or distribution-level namespace uniqueness. The scope is one running
  project.

## Decisions

### Decision 1: Ownership map, not a duplicate scan

Keep one `dict[str, str]` mapping namespace to the package path that claimed it, populated
as entries are processed. A second claim by the *same* path is fine; a second claim by a
different path raises.

The alternative — collecting all namespaces and looking for duplicates — cannot express the
plugin case, where a package legitimately re-claims a namespace it already owns. The map
answers "who owns this" rather than "how many claimed this," and only the first question has
a correct answer for plugins.

Populated in app order first, so an app always wins ownership over a plugin reference. That
ordering makes the error deterministic and makes the app list the authority, which is where
an author looks.

### Decision 2: `as` for the explicit namespace

An app entry is `"<module.path>"` or `"<module.path> as <namespace>"`.

`as` is Python's own vocabulary for rebinding a name to avoid a clash, so the meaning is
already known to every user of this framework — nothing new to learn, which is the DX bar
this project holds itself to. It does not overload `:`, which already means "attribute" in
`module.path:attribute` (`--framework`, and the `<app-path>.<module>.<attribute>` plugin
reference form).

Parsing splits on the delimiter ` as `, surrounded by whitespace, so a module path
containing the letters `as` is unaffected. Both sides are stripped; the right side goes
through `validate_segment("namespace", …)` exactly as a derived segment does, so the
grammar has one enforcement point.

A separate `[spoc.namespaces]` table was rejected: it puts the alias far from the entry it
modifies, and makes the reader consult two places to learn one app's namespace.

### Decision 3: Fail before registering anything

The ownership map is built from the full app list before any module is imported. A
contested namespace therefore fails with nothing registered, rather than partway through
with some components installed.

This matters beyond tidiness: the current failure mode is a duplicate-identifier error
raised mid-discovery, which is exactly the confusing artifact this change removes. Trading
it for a different mid-discovery error would keep the confusion.

### Decision 4: `ConfigurationError`, not a new exception type

The failure is a statement about the declarative file — two entries that cannot both be
true — which is what `ConfigurationError` already means, and it already carries the config
file path. A new type would add a public name to the surface (and a stability tier to
maintain) for a case that no caller can meaningfully handle differently: the only response
is to edit the file.

This departs from the proposal's initial sketch of a dedicated error. Recorded here rather
than silently changed.

### Build-vs-adopt gate

Recorded by `/ai:decide`; the same blocks appear in `DECISIONS.md`.
### Decision: Namespace-collision model — Adopt Django's app-label contract, build the check

- **Status**: approved
- **Why**: Django solved this exact problem with this exact derivation. `AppConfig.label`
  defaults to the last component of the app's dotted path, and two apps resolving to one
  label raise `ImproperlyConfigured: Application labels aren't unique, duplicates: <label>`
  at startup; the documented fix is a custom `AppConfig` stating an explicit `label`. The
  model — derive by default, fail loudly on contest, allow an explicit override — is what
  is adopted. The *code* is built, because there is nothing to install: the enforcement is
  a `dict[str, str]` from namespace to owning package inside `Framework`, and it is domain
  logic about SPOC's own identifier grammar (Rule 11), not a general concern any library
  could hold. One improvement on the precedent: Django's error names the duplicated label
  but not which apps produced it — a recurring complaint in its issue tracker — so ours
  names the namespace *and* both claiming paths.
- **Considered**: auto-disambiguating a collision by prefixing the parent segment
  (`vendor_shop`) — rejected because a component's identity would then change depending on
  which other apps happen to be installed, which is a worse failure than the one being
  fixed. Leaving the merge and relying on the existing duplicate-identifier error — rejected
  because that error only fires when object names also coincide, and names a third place
  when it does.
- **Isolation**: one ownership map built in `Framework._register_apps` before any import,
  consulted by `_register_plugins`. No new module, no dependency, no public type.

### Decision: Explicit-namespace syntax — Adopt Python's `as` convention, build the split

- **Status**: approved
- **Why**: `"vendor.shop as vendor_shop"` reuses the language's own vocabulary for rebinding
  a name to avoid a clash, so there is nothing new to learn — the DX bar this project holds.
  It also avoids overloading `:`, which already means "attribute" in `module.path:attribute`
  (the `--framework` reference and the plugin reference form). Parsing is a split on ` as `
  with surrounding whitespace, which a dotted module path cannot contain; a parser library
  for this would be more code to configure than to write, and would be the `loc` mistake
  again.
- **Considered**: a separate `[spoc.namespaces]` table (explicit, but puts the alias far
  from the entry it modifies, so a reader consults two places to learn one app's namespace);
  a `:` suffix (consistent punctuation, but `:` already means "attribute" in this project's
  own reference syntax, so it would make one delimiter mean two things).
- **Isolation**: parsed once where app entries are read, immediately validated by the
  existing `validate_segment("namespace", …)`, so the grammar keeps one enforcement point.

## Risks / Trade-offs

**A project relying on the merge breaks.** Deliberate, and the point. Nothing ships on SPOC
yet, so the population affected is zero and grows monotonically from here — this is the
cheapest moment this change will ever have.

**` as ` inside a module path.** Impossible: the delimiter requires surrounding whitespace,
and a dotted module path cannot contain whitespace. A malformed entry like `"a as"` yields
an empty namespace, which `validate_segment` rejects with the grammar.

**The plugin rule could be read as too strict.** A reference from outside any installed
app — `acme_billing.hooks.Charge`, a third-party distribution — claims namespace
`acme_billing`, which no app owns. That succeeds, and should: it is the primary use of
plugin groups. Only a claim on a namespace *another* package already owns fails.

**Ordering is now observable.** Apps claim before plugins, so which side of a collision is
reported as "the owner" depends on that order. Accepted: the error names both packages, so
the report is complete either way, and a stable rule beats an arbitrary one.
