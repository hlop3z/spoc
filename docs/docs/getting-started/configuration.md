# The Settings File

SPOC reads exactly **one** file: `spoc.toml`. It looks for it in two places,
in this order:

1. `<project>/config/spoc.toml` ← what `spoc init` creates
2. `<project>/spoc.toml`

Anything else in your `config/` folder — a `settings.py`, your own constants —
is **yours**. SPOC never imports it.

## The five keys

The `[spoc]` table has exactly five keys. Use a key outside this set and SPOC
refuses to start, naming the typo — your project never silently boots with
defaults it didn't ask for.

```toml title="config/spoc.toml"
[spoc]
mode = "development"   # which mode to boot in
debug = true           # yours to read from framework.config.project

[spoc.apps]            # which apps to install, per mode
production = ["apps.core"]
staging = []
development = ["apps.blog"]

[spoc.plugins]         # extra components declared by reference (see Learn → Plugins)

[spoc.modes]           # optional: your own modes (see below)
```

Every key is optional. A missing key falls back to a sensible default; a
missing file boots an empty project in `development` mode.

## Modes: one project, different outfits

A **mode** is the answer to "which apps should boot?" The three built-in modes
*cascade* — each one includes the ones to its right:

| Mode          | Boots the apps listed under…            |
| ------------- | --------------------------------------- |
| `production`  | `production`                            |
| `staging`     | `staging`, then `production`            |
| `development` | `development`, `staging`, `production`  |

So an app listed under `production` boots in **every** mode, and an app listed
under `development` boots only while you develop. Order is kept, duplicates
load once.

Need your own mode? Declare it under `[spoc.modes]` — your entries merge over
the defaults, so you never restate the built-in three:

```toml
[spoc.modes]
test = ["test", "production"]   # "test" boots test apps plus production apps

[spoc.apps]
production = ["apps.core"]
test = ["apps.fakes"]
```

## Your own tables: app-owned settings

SPOC claims exactly **one** top-level table: `[spoc]`. Every other top-level
table in the file is yours — parsed and handed back untouched on
`framework.config.tables`, never validated or read by the kernel. SPOC will
never claim a second table, so a table of yours can never collide with a
kernel one.

```toml title="config/spoc.toml"
[spoc]
mode = "development"
debug = true

[myapp]                # yours: any keys, any shapes
api_url = "https://api.example.com"
retries = 3
```

```python title="main.py"
from pathlib import Path

import spoc

BASE_DIR = Path(__file__).resolve().parent

framework = spoc.Framework()          # a settings-only project — no kinds yet
framework.start(BASE_DIR)

settings = framework.config.tables["myapp"]   # {'api_url': ..., 'retries': 3}
print(settings["retries"])                    # 3
```

**Validating your tables is your job**, with any schema tool you like — the
table arrives as a plain dict, so any validator that accepts one fits the
seam. The worked, runnable example (a plain pydantic model over the
already-parsed table) is [Validate Your Settings](../how-to/validate-settings.md).

A typo inside `[spoc]` still refuses to boot, loudly. A typo inside your own
table is yours to catch — at the boundary, before the bad value travels.

## Per-mode environment values

Beside the settings file, SPOC loads one small TOML file per mode from
`config/.env/` (or `.env/` at the project root):

```
config/
├── spoc.toml
└── .env/
    ├── development.toml
    ├── production.toml
    └── default.toml      # fallback when the mode has no file
```

Each file holds an `[env]` table with whatever you want in it:

```toml title="config/.env/development.toml"
[env]
database_url = "sqlite:///dev.db"
```

## Reading your settings back

After `start()`, everything is on `framework.config`:

```python title="main.py"
from pathlib import Path

import spoc

BASE_DIR = Path(__file__).resolve().parent

framework = spoc.Framework()
framework.start(BASE_DIR)

print(framework.config.project["debug"])             # True — the [spoc] table
print(framework.config.environment["database_url"])  # the active mode's env file
print(framework.config.tables["myapp"])              # your tables, as parsed
print(framework.installed_apps)                      # [] — none installed here
```

Next: [the starter template](starter.md), or jump to
[the framework object](../learn/framework.md).
