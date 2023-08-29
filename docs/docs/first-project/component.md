As you journey into crafting dynamic applications using the **S.P.O.C** framework, creating custom components is a fundamental skill to master. Components encapsulate discrete units of functionality, promoting modularity, reusability, and maintainability within your project.

<div id="terminal-component" data-termynal></div>

## Creating a Component: **@Decorator**

```python title="framework/components.py"
# -*- coding: utf-8 -*-
"""{ Components } Read The Docs"""

import functools
import spoc
import click

COMPONENTS = {}
COMPONENTS["commands"] = {"type": "commands"}

# Decorator: `@commands`
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

    # Real Wrapper (click)
    cls = click.group(cls)

    # Register as a `SPOC` Component if not a command group.
    if not group:
        spoc.component(cls, metadata=COMPONENTS["commands"])

    # Return Modified Class
    return cls
```

<div id="terminal-component-commands" data-termynal></div>

## Using the Component: **`@commands`**

By marking your function with the **`@commands`** decorator. This annotation flags the function as a **component** and **registers** it for future use.

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
