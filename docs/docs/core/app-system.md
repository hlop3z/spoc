# App System

SPOC organizes code into **apps**: self-contained Python packages declared
as dotted module paths in `[spoc.apps]` and imported through Python's normal
import system, exactly as written. The app is also the unit of identity —
the final segment of its declared path is the `namespace` segment of every
component it declares: `apps.blog` declares under `blog`.

## Layout

```
myproject/
├── apps/                  # a package — has __init__.py
│   ├── __init__.py
│   ├── blog/
│   │   ├── __init__.py
│   │   ├── models.py      # kind "models"
│   │   └── views.py       # kind "views"
│   └── shop/
│       ├── __init__.py
│       ├── models.py
│       └── views.py
├── config/
│   └── spoc.toml
└── main.py
```

The kernel never mutates `sys.path` and never creates directories. Running
the entry point (`python main.py`) makes its directory importable, which is
all the `apps/` package needs — `apps.blog` and `apps.shop` import like any
other package. An app path that cannot be imported fails start with
`AppNotFoundError` naming the declared path.

The module files each app must provide are the framework's declared kinds —
`spoc.Framework("models", "views")` means every app has `models.py` and
`views.py`. A missing module for a required kind is a startup error; for a
kind declared `required=False` it is skipped.

!!! note "Namespace rules"
    The final segment of the declared app path becomes an identifier
    segment, so it must be lowercase snake_case (`^[a-z][a-z0-9_]*$`). An
    app declared as `apps.MyApp` fails at startup with
    `InvalidSegmentError`.

## Selecting apps

Apps are declared per mode in `[spoc.apps]` — the only source:

```toml
[spoc]
mode = "development"

[spoc.apps]
production  = ["apps.auth"]
staging     = ["apps.reports"]
development = ["apps.sandbox"]
```

| mode | apps loaded |
| --- | --- |
| `production` | apps.auth |
| `staging` | apps.reports, apps.auth |
| `development` | apps.sandbox, apps.reports, apps.auth |

Order is preserved and duplicates are dropped. Identifiers keep the short
namespace — `apps.auth`'s models register as `models:auth.*`.

The cascade above is the default triple; `[spoc.modes]` declares further
modes that merge over it — see
[Configuration](../getting-started/configuration.md#declaring-modes).

## Mode cascade as adapter selection

Because lower modes include higher ones, registering alternative
implementations as *different apps* makes the cascade select adapters:

```toml
[spoc.apps]
production  = ["apps.comfyui_engine"]    # the real thing
development = ["apps.fake_engine"]       # a fake for local work
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
