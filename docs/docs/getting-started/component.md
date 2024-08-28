As you journey into crafting dynamic applications using the **S.P.O.C** framework, creating custom components is a fundamental skill to master. Components encapsulate discrete units of functionality, promoting modularity, reusability, and maintainability within your project.

## Creating a Component: **@Decorator**

```python title="framework/components.py"
# -*- coding: utf-8 -*-
"""{ Components } Read The Docs"""

from typing import Any
import functools
import spoc
import click

components = spoc.Components()
components.add("command", {"is_click": True})

def command(obj: Any = None, *, group: bool = False):
    """Click Commands and Groups"""
    if obj is None:
        return functools.partial(command, group=group)

    # Real Wrapper (click)
    obj = click.command(obj) if not group else click.group(obj)
    components.register("command", obj)

    # Return Modified Class
    return obj

```

## Using the Component: **`@command`**

By marking your function with the **`@command`** decorator. This annotation flags the function as a **component** and **registers** it for future use.

```python title="apps/demo/commands.py"
# -*- coding: utf-8 -*-
"""{ Commands } Read The Docs"""

from framework import commands
import click

@command(group=True)
def cli():
    "Click Group"

@cli.command()
def other_cmd():
    click.echo("Other (Command)")

@command
def hello_world():
    click.echo("Hello World (Command)")
```
