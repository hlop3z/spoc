# Quick Start

Build a minimal SPOC project: one app, one kind, resolved through the
registry. There is one way to do this — declare, mark, start.

## Generate it

```bash
spoc init myproject
cd myproject
python main.py
```

```
Ready: 2 components registered
Installed apps: ['apps.core']
 - models:core.example
 - views:core.example
```

That is a complete, running project. `spoc init` ships with the package and
needs nothing else installed.

If SPOC is not installed yet, `uvx` runs the generator without installing anything —
the project still needs SPOC in the environment you run it from:

```bash
uvx spoc init myproject
cd myproject
uv venv && uv pip install spoc
python main.py
```

See [Installation](installation.md#using-uvx-run-the-scaffolder-without-installing)
for the full picture.

Useful flags: `--kinds` sets the declared kind set (`--kinds models,views,tasks`),
`--app` names the starter app, `--path` chooses the destination.

The rest of this page explains what was generated. Read it once and you will
not need the generator again — a SPOC app is a directory with a module per
kind, which is quicker to copy than to scaffold.

## Project layout

```
myproject/
├── apps/
│   ├── __init__.py          # apps/ is a package
│   └── core/
│       ├── __init__.py
│       ├── models.py        # objects here are kind "models"
│       └── views.py         # objects here are kind "views"
├── config/
│   └── spoc.toml            # the only file the kernel reads
├── framework.py             # the whole framework definition
└── main.py
```

Layout **is** taxonomy: objects declared in `<app>/models.py` are components
of kind `models`, and the final segment of the declared app path is the
namespace — `apps.core` declares under `core`.

Apps are imported through Python's normal import system, exactly as declared.
The kernel never mutates `sys.path` and never creates directories; running
`main.py` makes its directory importable, which is all the `apps/` package
needs.

## 1. Declare the framework

`framework.py` — the kind set is stated exactly once, here:

```python
import spoc

framework = spoc.Framework("models", "views")

model = framework.kind("models")
view = framework.kind("views")
```

That's the entire framework definition. `framework.kind()` returns a
ready-made decorator; asking for an undeclared kind raises
`UnknownKindError` naming the declared set.

## 2. Configure

`config/spoc.toml`:

```toml
[spoc]
mode = "development"
debug = true

[spoc.apps]
production = ["apps.core"]
```

Each entry is a dotted module path, imported exactly as written. An app path
that cannot be imported fails start with `AppNotFoundError` naming the
declared path. Apps are declared per mode and `development` cascades
`staging` and `production` in, so an app listed under `production` loads in
every mode.

Every key is optional — absent keys use defaults. The `[spoc]` table is a
closed set, so a mistyped key fails start naming it rather than merging
silently. No `settings.py` is needed; if you have one, it is yours and SPOC
never reads it.

## 3. Declare components

`apps/core/models.py`:

```python
from framework import model

@model
class Post:                        # → models:core.post
    ...

@model
class CommentThread:               # → models:core.comment_thread
    ...
```

Write normal PEP 8 Python. The identifier is derived from the class name in
snake_case, so `CommentThread` becomes `comment_thread` — no restating it.
Functions work the same way (`def list_posts` → `list_posts`).

Pass `name=` only when you want an identifier that *differs* from the object's
name. A name you state is used verbatim and validated, never converted:

```python
@model(name="legacy_user")         # → models:core.legacy_user
class UserAccount:
    ...

@model(name="LegacyUser")          # InvalidSegmentError — you stated it, so it must conform
class Other:
    ...
```

!!! note "Derivation converts; nothing else does"
    Conversion happens once, when deriving a name from the object. Lookups
    are exact — `resolve("models:core.Post")` fails, because
    `models:core.post` is the one canonical identifier.

## 4. Start and use the registry

`main.py`:

```python
from pathlib import Path
from framework import framework

framework.start(Path(__file__).resolve().parent)

# Resolve one component by canonical identifier
record = framework.resolve("models:core.post")
print(record.identifier)   # models:core.post
print(record.kind)         # models
print(record.namespace)    # core
print(record.object_name)  # post
print(record.object)       # <class 'apps.core.models.Post'>

# Enumerate everything (deterministic order)
for component in framework.registry:
    print(component.identifier)

# Facet views are derived from the same flat store
framework.registry.by_kind("models")
framework.registry.by_namespace("core")

framework.shutdown()
```

Construction is inert — nothing happens until `start(base_dir)`. `base_dir`
locates configuration only: `config/spoc.toml` (or `spoc.toml`) and the
`.env` directories. Starting twice raises; `shutdown()` before `start()` is a
harmless no-op. In an async application, `astart(base_dir)` and `ashutdown()`
mirror the pair.

## Precise failures

A typo never falls through to `None` — every failed resolution names the
failing segment and the valid candidates:

```python
framework.resolve("modle:core.post")
# UnknownKindError: Unknown kind 'modle'. Declared kinds: models, views

framework.resolve("models:cor.post")
# UnknownNamespaceError: Unknown namespace 'cor' for kind 'models'.
# Namespaces with 'models' components: core

framework.resolve("models:core.pots")
# UnknownObjectError: Unknown object_name 'pots' in models:core.
# Registered: comment_thread, post

framework.resolve("models:core.post.create")
# MalformedIdentifierError: an operation suffix is not part of the grammar
```

## Project a surface from the registry

The registry record carries everything a surface needs — build routes without
touching kernel internals:

```python
def build_routes(registry):
    return [
        {"method": "GET", "path": f"/{c.namespace}/{c.object_name}", "endpoint": c.object}
        for c in registry.by_kind("views")
    ]
```

See the [Basic Example](../examples/basic.md) for the full working project,
including a FastAPI projection.

## Adding a second app

There is no `spoc add-app`, deliberately. An app is a directory with an
`__init__.py` and a module per kind — copy the generated one:

```bash
cp -r apps/core apps/billing
```

Then register it in `config/spoc.toml`:

```toml
[spoc.apps]
production = ["apps.core", "apps.billing"]
```

That is the whole operation. Anything a generator could do here you can do in
two commands, and the app you copy is already correct for your kind set.

## Your own template set

A framework built on SPOC can ship its own project shape and get `init`
against it without writing a generator. A template set is a directory of files
in the format they are emitted as, plus a manifest declaring its substitution
values:

```toml
# manifest.toml
[template_set]
name = "myframework"
values = ["project_name", "app_name", "kinds_args", "kind_decorators", "kind"]

[[files]]
source = "config/spoc.toml.tmpl"
target = "config/spoc.toml"

# Emitted once per declared kind, with `kind` bound each time.
[[files]]
source = "app/kind.py.tmpl"
target = "apps/$app_name/$kind.py"
per_kind = true
```

Templates use `$name` substitution and nothing else — no expressions, no
conditionals. Content is never executed during generation, so a template that
looks like runnable code is emitted verbatim. Repetition is declared by the
manifest (`per_kind`), never expressed inside a template.

Register it under the `spoc.scaffold_templates` entry-point group — the entry
point may resolve to a directory path or to the importable package holding the
files, so a zipped install works either way — then
`spoc init myproject --template myframework`. Every placeholder a template uses
must appear in `values`; both directions are checked before anything is written.

## Next steps

- [Configuration](configuration.md) — modes, environments, and the app cascade
- [Framework](../core/framework.md) — declaration and lifecycle in detail
- [Components](../core/components.md) — declaration rules and the identifier grammar
