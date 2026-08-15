# The Starter

The `default` template gives you the smallest thing that boots. The **starter**
gives you a running application: the [default vocabulary](../learn/vocabulary.md)
wired end to end, a working CLI, and a projection module ready to bind to any
transport — with **zero dependencies beyond SPOC itself**.

```bash
spoc init myproject --template starter
cd myproject
python main.py --help
```

```text
usage: myproject [-h] {core.add,core.items} ...

positional arguments:
  {core.add,core.items}
    core.add            Add an item to the store.
    core.items          List the items in the store.

options:
  -h, --help            show this help message and exit
```

That help text was not written anywhere — it is a **projection**. `surface.py`
derives a command table from the registry; `cli.py` binds that table to
argparse. Run one:

```bash
python main.py core.add milk
```

```text
added 'milk' (1 total)
[core] core.add finished     ← a hook, dispatched by the surface
```

## What was generated

```
myproject/
├── config/spoc.toml     # the one file SPOC reads; other tables are yours
├── framework.py         # the five-kind vocabulary — resources carry hooks
├── surface.py           # registry → abstract route/command/hook tables
├── cli.py               # argparse over surface.commands — a thin adapter
├── main.py              # boot, dispatch, shut down
└── apps/core/           # one module per kind: models, views, commands,
                         #   resources, hooks
```

Note what is _not_ here: no web framework, no message library, nothing to
`pip install`. The starter chooses no transport for you — `--kinds` does not
apply to it, and the vocabulary is written out in full so you can rename or
delete what you don't need.

## Grow it

- **A new command**: add a `@command` function to `apps/core/commands.py`. It
  becomes a subcommand — no edit to `cli.py`.
- **A new app**: `spoc app billing` generates the five modules; add
  `"apps.billing"` to a mode list in `config/spoc.toml`.
- **A resource**: declare an instance with `open()`/`close()` in
  `resources.py` — the kind's hooks handle its lifetime. The full recipe is in
  [The Default Vocabulary](../learn/vocabulary.md).

## Bind a transport

`surface.routes(registry)` already derives an abstract route table from your
views. Binding it to a real transport is a few lines _in your project_, using
whatever you prefer — the worked, runnable FastAPI example is
[Bind a Transport](../how-to/bind-a-transport.md), and the same loop shape
serves a message socket or a worker queue. SPOC never chooses your transport,
and your components never know which one called them.

Next: [The Default Vocabulary](../learn/vocabulary.md) explains what each kind
means, or jump to [the storefront example](../examples.md) for a three-app
project.
