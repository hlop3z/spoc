# Configuration

The kernel reads exactly one declarative file: **`config/spoc.toml`** (or
`spoc.toml` at the project root). Nothing else is required or consulted —
a `settings.py`, if you keep one, is yours alone and SPOC never imports it.

## spoc.toml

```toml
[spoc]
mode = "development"      # development | staging | production
debug = true

[spoc.apps]
production  = ["auth"]
staging     = ["reports"]
development = ["sandbox"]

[spoc.plugins]
middleware = ["demo.extras.middleware"]
hooks      = ["demo.extras.hook"]
```

Every key is optional. Absent keys fall back to defaults:

| Key | Default |
| --- | --- |
| `mode` | `"development"` |
| `debug` | `false` |
| `apps` | `{}` |
| `plugins` | `{}` |

A missing `spoc.toml` starts the framework with all defaults and logs a
warning naming the expected locations.

## The mode cascade

Apps are declared per mode, and lower modes include higher ones:

| mode | apps loaded |
| --- | --- |
| `production` | production |
| `staging` | staging, then production |
| `development` | development, then staging, then production |

Order is preserved; duplicates keep their first position. With the file
above, `development` loads `sandbox, reports, auth`.

Because lower modes include higher ones, registering alternative
implementations as *different apps* makes the cascade select adapters —
a `fake_engine` app in `development` and the real one in `production`,
with no `if mode == ...` branching anywhere.

## Plugins

`[spoc.plugins]` groups loadable references, each in the form
`package.module.attribute`. Each group names a **declared kind**, and every
loaded object registers in the same flat registry as discovered components —
here, `hooks:demo.hook`. A reference that cannot be resolved — or a group
that is not a declared kind — fails start, naming the offender:

```python
framework.start(BASE_DIR)
framework.resolve("hooks:demo.hook").object   # the loaded object
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
