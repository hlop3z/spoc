# Error Index

Every error SPOC raises is on this page. Each is a subclass of `SpocError`, so
`except spoc.SpocError` catches them all — and each names precisely what
failed. Match on the **type**, never the message text: the wording may improve
in any release; the types and their hierarchy are the
[stable surface](stability.md).

This index is verified against the package's exported exceptions by the test
suite — a new error type cannot ship without a row here.

## The catch-all

| Error | When it happens | The fix |
| --- | --- | --- |
| `SpocError` | Never raised itself — it's the base every kernel error subclasses. | Catch it when any SPOC failure should take one code path. |

## Settings and boot

| Error | When it happens | The fix |
| --- | --- | --- |
| `ConfigurationError` | `spoc.toml` didn't load or a `[spoc]` key is outside the five allowed. | Fix the named key — the message says which one; see [The Settings File](../getting-started/configuration.md). |
| `AppNotFoundError` | An installed app's dotted path doesn't import. | Check the entry under `[spoc.apps]` against the folder on disk — the path is imported exactly as written; see [Apps & Modes](../learn/apps.md). |
| `MissingModuleError` | An app has no module for a kind that requires one. | Add the module file, or declare the kind `required=False` if apps may omit it; see [Apps & Modes](../learn/apps.md). |
| `CircularDependencyError` | `depends_on` between kinds forms a cycle — the cycle is named. | Break the cycle in the `KindSpec` declarations; see [The Framework Object](../learn/framework.md). |

## The name grammar

| Error | When it happens | The fix |
| --- | --- | --- |
| `MalformedIdentifierError` | A string doesn't parse as `kind:namespace.object_name`. | Spell the tag with all three segments — `models:blog.post`; see [Name Tags](../learn/names-and-registry.md). |
| `InvalidSegmentError` | A segment breaks the `^[a-z][a-z0-9_]*$` grammar — stated names are never rewritten. | Rename to lowercase snake_case, or drop `name=` and let SPOC derive it; see [Name Tags](../learn/names-and-registry.md). |

## Resolution

| Error | When it happens | The fix |
| --- | --- | --- |
| `UnknownKindError` | The kind segment isn't in the declared kind set. | Declare the kind on the `Framework`, or fix the typo — the message lists the valid kinds. |
| `UnknownNamespaceError` | No components of that kind exist in that namespace. | Install the app that provides it, or fix the segment — the message lists the registered namespaces. |
| `UnknownObjectError` | Kind and namespace matched; the object name didn't. | Fix the last segment — the message lists what *is* registered there. |
| `UnresolvedReferenceError` | A plugin reference (`module.attribute` in `[spoc.plugins]`) names something that doesn't exist. | Correct the dotted reference in `spoc.toml`; see [Plugins](../learn/plugins.md). |
| `FrameworkTransitioningError` | The tag is fine — the timing isn't. Something resolved while `start` or `shutdown` was in flight, from outside that transition. | Order the read against the transition. In a served app, shut down where your server has already finished in-flight work — the ASGI lifespan shutdown handler, or after a gRPC `stop(grace)` returns. See [Shipping a framework](../how-to/ship-a-framework.md). |

## Registration

| Error | When it happens | The fix |
| --- | --- | --- |
| `DuplicateComponentError` | A second, different object claimed an already-taken tag. | Rename one of them (`name=`) — two blocks can't share a tag. |
| `IdentityDivergenceError` | The same object was re-registered under a different identity. | Register a block once; re-registering the same tag is fine, a *new* tag is refused. |
| `ComponentKindMismatchError` | A block's declared kind doesn't match the module it lives in — layout is taxonomy. | Move the block to the kind's file (`models` block → `models.py`), or fix the decorator; see [Apps & Modes](../learn/apps.md). |
| `MissingNameError` | An object with no `__name__` (an instance) was registered without `name=`. | Name it explicitly: `resource(Database(), name="database")`; see [The Default Vocabulary](../learn/vocabulary.md). |
| `UnmarkableObjectError` | The object can't carry the declaration marker (e.g. a builtin or a slotted instance). | Wrap it in something markable, or register a factory/class instead. |
| `MetadataContractError` | A block's metadata departs from what its kind's `metadata` class demands — extra, missing, or wrongly typed. | Hand in an instance of the declared class: `@view(meta=Route(path=…))`; see [The Framework Object](../learn/framework.md). |
| `ComponentShapeError` | `resolve_type` was asked for something that isn't a class, or `resolve_object` for something that is. | Use the accessor matching the block's shape — `resolve_type` for a class, `resolve_object` for an instance or a function. Only the shape is checked; whether the object *matches* your contract is your type checker's question, see [Get Editor Autocomplete](../how-to/get-editor-autocomplete.md). |

`spoc.formats` has its own family under `FormatError` — those render in
[the toolbox reference](tooling.md), and the one to catch is `FormatError`.

Next: [Stability & Versioning](stability.md).
