<div id="terminal-component" data-termynal></div>

## Component(s): **@Decorator**

```python title="framework/components.py"
# -*- coding: utf-8 -*-
"""{ Components } Read The Docs"""

import functools
import spoc
import click

components = {}
components["commands"] = {"type": "commands"}

# Class @Decorator
def commands(
    cls: object = None,
    *,
    group: bool = False,
):
    """Click { CLI } Creator"""
    if cls is None:
        return functools.partial(
            commands,
            group=group,
        )
    # Real Wrapper
    cls = click.group(cls)
    if not group:
        spoc.component(cls, metadata=components["commands"])
    return cls
```

<div id="terminal-component-commands" data-termynal></div>

## Component(s): **Commands**

```python title="apps/demo/commands.py"
# -*- coding: utf-8 -*-
"""{ Commands } Read The Docs"""

from framework import commands
import click

@commands
def cli():
    "Click Group"


@cli.command()
def hello_world():
    "Hello World (Docs)"

    click.echo("Hello World (Commands)")
```
