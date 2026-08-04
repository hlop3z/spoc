# App System

SPOC organizes code into **apps**: self-contained packages in an `apps/`
directory, discovered and loaded by the framework. The app is also the unit
of identity — its package name is the `namespace` segment of every component
it declares.

## Layout

```
myproject/
├── apps/
│   ├── blog/
│   │   ├── __init__.py
│   │   ├── models.py      # kind "models"
│   │   └── views.py       # kind "views"
│   └── shop/
│       ├── __init__.py
│       ├── models.py
│       └── views.py
└── config/
    └── spoc.toml
```

`start(base_dir)` puts `apps/` on the import path, so apps import as
top-level packages: `blog.models`, `shop.views`.

The module files each app must provide are the framework's declared kinds —
`spoc.Framework("models", "views")` means every app has `models.py` and
`views.py`. In `strict` mode a missing module file is a startup error; in
`loose` mode it is skipped.

!!! note "Namespace rules"
    The app directory name becomes an identifier segment, so it must be
    lowercase snake_case (`^[a-z][a-z0-9_]*$`). An app named `MyApp` fails
    at startup with `InvalidSegmentError`.

## Selecting apps

Apps are declared per mode in `[spoc.apps]` — the only source:

```toml
[spoc]
mode = "development"

[spoc.apps]
production  = ["auth"]
staging     = ["reports"]
development = ["sandbox"]
```

| mode | apps loaded |
| --- | --- |
| `production` | auth |
| `staging` | reports, auth |
| `development` | sandbox, reports, auth |

Order is preserved and duplicates are dropped.

## Mode cascade as adapter selection

Because lower modes include higher ones, registering alternative
implementations as *different apps* makes the cascade select adapters:

```toml
[spoc.apps]
production  = ["comfyui_engine"]    # the real thing
development = ["fake_engine"]       # a fake for local work
```

Both apps declare components under their own namespace; surfaces resolve
whichever namespace convention the mode brought in — no `if mode == ...`
branching anywhere.

## Dependencies between modules

A kind's `depends_on` orders module loading *within* every app:

```python
spoc.Framework(
    "models",
    spoc.KindSpec("views", depends_on=("models",)),   # views load after models
)
```

The loader topologically sorts `<app>.<module>` nodes; circular dependencies
raise `CircularDependencyError` at startup.

## Apps need not implement every kind

A kind declared `required=False` may be absent from any app — that app simply
contributes no components of it:

```python
spoc.Framework("models", spoc.KindSpec("views", required=False))
```

Optionality is per kind, so this does not weaken the guarantee for `models`:
an app missing `models.py` still fails start with `MissingModuleError`. A
module that *exists* but fails to import is an error regardless.

## Module lifecycle functions

Any app module may define:

```python
def initialize():   # called during startup, in dependency order
    ...

def teardown():     # called during shutdown, in reverse order
    ...
```

See [Lifecycle Hooks](../advanced/lifecycle.md) for schema-level hooks.
