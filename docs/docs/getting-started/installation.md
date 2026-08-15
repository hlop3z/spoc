# Install

SPOC needs **Python 3.12 or newer**. That's it — the core has zero
dependencies.

```bash
pip install spoc
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add spoc
```

For an application you'll deploy, pin the major:

```bash
pip install "spoc>=1.0,<2"
```

That range is exactly what the [stability contract](../api/stability.md)
promises against — see [Upgrading](../api/migration.md) for why nothing
tighter is needed.

## Check it worked

The `spoc` command line tool comes with the package:

```bash
spoc --version
spoc --help
```

## Extras (only if you want them)

Everything the kernel does works on a bare install. A few _optional_ features
of [`spoc.formats`](../tools/formats.md) and
[`spoc.testing`](../tools/testing.md) need one extra package each:

| Extra   | Install                     | What it unlocks                       |
| ------- | --------------------------- | ------------------------------------- |
| `yaml`  | `pip install "spoc[yaml]"`  | Reading and writing YAML files        |
| `xml`   | `pip install "spoc[xml]"`   | Reading and writing XML files         |
| `toml`  | `pip install "spoc[toml]"`  | _Writing_ TOML (reading is built in)  |
| `query` | `pip install "spoc[query]"` | JSONPath queries with `formats.query` |
| `full`  | `pip install "spoc[full]"`  | All of the above                      |

!!! tip "You can't pick wrong"
If you use a feature whose extra is missing, SPOC tells you exactly which
one to install. Nothing fails silently.

Next: [build your first project](quick-start.md).
