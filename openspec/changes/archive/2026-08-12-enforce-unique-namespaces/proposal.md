## Why

A component's namespace derives from the final segment of its app's declared module path,
so two apps at different paths whose folders share a name — `apps.shop` and `vendor.shop`,
`billing.api` and `shipping.api` — silently register into one namespace. Nothing reports
it. The merge stays invisible until the two apps happen to declare the same object name,
at which point a duplicate-identifier error names a third place and the author has no
reason to suspect the layout.

Nesting app packages under a container directory is what every project does past a handful
of apps, and it is exactly what makes leaf-name collisions likely. The identifier grammar
promises that `kind:namespace.object_name` names one thing; two packages answering to one
namespace breaks that promise quietly, which is the worst way for it to break.

## What Changes

- Two installed apps resolving to the same namespace **fail at start**, naming the
  namespace and both claiming paths, instead of merging.
- An app entry may state its namespace explicitly as `"<module.path> as <namespace>"`,
  so a collision is resolvable without renaming a package the author may not control
  (a vendored tree, a third-party distribution).
- A `[spoc.plugins]` reference whose derived namespace is already claimed by a different
  package fails the same way. Registering into an installed app's own namespace stays
  legal — that is what the group is for.
- **BREAKING** for any project that today relies on two apps sharing a namespace. Nothing
  ships on SPOC yet, so the cost is zero now and grows from here.

## Capabilities

### New Capabilities

<!-- None. This constrains an existing declaration, it does not introduce a surface. -->

### Modified Capabilities

- `project-configuration`: the app-declaration requirement gains namespace uniqueness and
  the explicit-alias form; the plugin requirement gains the matching ownership rule.
- `object-identity`: the grammar's promise that one identifier names one thing is stated
  as a namespace-ownership invariant rather than left implicit.

## Impact

- `src/spoc/framework.py` — `_register_apps` and the plugin registration loop, which is
  where both namespaces are derived today.
- `src/spoc/core/exceptions.py` — one new error for a contested namespace.
- Configuration format: `[spoc.apps]` entries accept an optional `as` suffix. Existing
  entries are unaffected; the derived namespace remains the default and stays implicit.
- `tests/conformance/` — the fixture moves under a container package, so the layout the
  rule is about is the layout the stub gate exercises.
- No new dependencies. The check is a dictionary and a comparison.
