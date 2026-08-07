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

```python
framework.start(BASE_DIR)

framework.config.project["debug"]           # True — the [spoc] table
framework.config.environment["database_url"]  # from the active mode's env file
framework.installed_apps                    # ['apps.core', 'apps.blog']
```

Next: [the framework object](../learn/framework.md).
