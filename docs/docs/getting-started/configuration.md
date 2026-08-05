# Configuration

The kernel reads exactly one declarative file: **`config/spoc.toml`** (or
`spoc.toml` at the project root). `start(base_dir)` uses `base_dir` only to
locate this file and the `.env` directories. Nothing else is required or
consulted — a `settings.py`, if you keep one, is yours alone and SPOC never
imports it.

## spoc.toml

```toml
[spoc]
mode = "development"      # must name a mode in the effective set
debug = true

[spoc.apps]
production  = ["apps.auth"]
staging     = ["apps.reports"]
development = ["apps.sandbox"]

[spoc.plugins]
middleware = ["extras.middleware"]
hooks      = ["extras.hook"]
```

Each `[spoc.apps]` entry is a dotted module path, imported through Python's
normal import system exactly as written. The final segment is the app's
namespace (`apps.auth` → `auth`), validated against `^[a-z][a-z0-9_]*$`.
An app path that cannot be imported fails start with `AppNotFoundError`
naming the declared path.

Every key is optional. Absent keys fall back to defaults:

| Key | Default |
| --- | --- |
| `mode` | `"development"` |
| `debug` | `false` |
| `apps` | `{}` |
| `modes` | the default triple (see [Declaring modes](#declaring-modes)) |
| `plugins` | `{}` |

A missing `spoc.toml` starts the framework with all defaults and logs a
warning naming the expected locations.

## The mode cascade

Apps are declared per mode, and each mode names the cascade of app lists it
loads. The default triple:

| mode | apps loaded |
| --- | --- |
| `production` | production |
| `staging` | staging, then production |
| `development` | development, then staging, then production |

Order is preserved; duplicates keep their first position. With the file
above, `development` loads `apps.sandbox, apps.reports, apps.auth`.

Because lower modes include higher ones, registering alternative
implementations as *different apps* makes the cascade select adapters —
a `fake_engine` app in `development` and the real one in `production`,
with no `if mode == ...` branching anywhere.

## Declaring modes

`[spoc.modes]` maps a mode name to its cascade list:

```toml
[spoc.modes]
test = ["test", "production"]

[spoc.apps]
test = ["apps.fakes"]
```

Declared modes **merge over** the default triple — adding a mode never
requires restating `production`, `staging`, or `development`. A declared
name that collides with a default replaces that entry.

The active `mode`, every `[spoc.apps]` key, and every cascade entry must
name a mode in the effective set; a violation fails start with
`ConfigurationError` naming the valid modes.

## Plugins

`[spoc.plugins]` groups loadable references, each a dotted
`module.attribute` path importable exactly as written. Each group names a
**declared kind**, and every loaded object registers in the same flat
registry as discovered components, under the same grammar — the segment
before the module is the namespace, so `extras.hook` yields
`hooks:extras.hook` and `apps.demo.extras.hook` yields `hooks:demo.hook`
(see [Plugins](../advanced/plugins.md)). A reference
that cannot be resolved — or a group that is not a declared kind — fails
start, naming the offender:

```python
framework.start(BASE_DIR)
framework.resolve("hooks:extras.hook").object   # the loaded object
```

## Per-mode environment values

Environment values live in TOML files under `config/.env/` (or `.env/`),
one file per mode, under an `[env]` table:

```
config/.env/
├── development.toml
├── production.toml
└── default.toml        # fallback when no mode-specific file exists
```

```toml
# config/.env/development.toml
[env]
DATABASE_URL = "sqlite:///dev.db"
API_KEY = "dev-key"
```

Loading order: the mode-specific file wins; `default.toml` is the fallback;
neither existing yields empty values. The loaded mapping is available as
`framework.config.environment`.

!!! note "Secrets are not config"
    Reference secrets by key and inject them at runtime — never commit them
    to environment TOML files.

## Your own settings

Anything that needs Python — computed constants, conditional logic — goes in
a module you own (conventionally `config/settings.py`) and is imported by
*your* code, never by SPOC:

```python
# config/settings.py — yours; the kernel never touches it
import os

DEBUG_TOOLBAR = os.environ.get("DEBUG_TOOLBAR") == "1"
```
