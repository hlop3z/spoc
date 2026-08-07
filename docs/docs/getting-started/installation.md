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

## Check it worked

```bash
python -c "import spoc; print(spoc.__version__)"
```

The `spoc` command line tool comes with it:

```bash
spoc --help
```

## Extras (only if you want them)

Everything the kernel does works on a bare install. A few *optional* features
of [`spoc.formats`](../tools/formats.md) and
[`spoc.testing`](../tools/testing.md) need one extra package each:

| Extra  | Install                    | What it unlocks                          |
| ------ | -------------------------- | ---------------------------------------- |
| `yaml` | `pip install "spoc[yaml]"` | Reading and writing YAML files           |
| `xml`  | `pip install "spoc[xml]"`  | Reading and writing XML files            |
| `toml` | `pip install "spoc[toml]"` | *Writing* TOML (reading is built in)     |
| `query`| `pip install "spoc[query]"`| JSONPath queries with `formats.query`    |
| `full` | `pip install "spoc[full]"` | All of the above                         |

!!! tip "You can't pick wrong"
    If you use a feature whose extra is missing, SPOC tells you exactly which
    one to install. Nothing fails silently.

Next: [build your first project](quick-start.md).
