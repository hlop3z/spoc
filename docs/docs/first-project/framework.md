<div id="terminal-framework" data-termynal></div>

```python title="framework/framework.py"
# -*- coding: utf-8 -*-
"""{ Core } Read The Docs"""

import spoc
import click

PLUGINS = ["commands"]

@click.group()
def cli():
    "Click Main"

@spoc.singleton
class MyFramework:
    """Framework"""

    def init(
        self,
    ):
        """Class __init__ Replacement"""
        framework = spoc.App(plugins=PLUGINS)

        # Run Extras
        before_server = framework.extras['before_server']
        for method in before_server:
            method()

        # INIT Command(s) Sources
        command_sources = [cli]

        # Collect All Commands
        for active in framework.component.commands.values():
            command_sources.append(active.object)

        title = "My Project"
        help_text = f"""
        Welcome to { title }
        """

        self.cli = click.CommandCollection(
            name=title,
            help=help_text,
            sources=command_sources
        )
```
