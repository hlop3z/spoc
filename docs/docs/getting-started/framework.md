Creating your framework using the **S.P.O.C** foundation is an exciting endeavor that empowers you to construct powerful and flexible applications with ease. A framework serves as a structured blueprint that streamlines development, promotes consistency, and accelerates the creation of feature-rich projects.

```python title="framework/framework.py"
# -*- coding: utf-8 -*-
"""{ Framework } Read The Docs"""

from typing import Any

import click
import spoc

TITLE = "My Project"
MODULES = ["commands", "models", "views"]

@click.group()
def cli():
    "Click Main"

def handle_commands(items: list):
    """Collect (Click) Commands"""

    # INIT Command(s) Sources
    command_sources = [cli]

    # CLI Banner
    help_text = f"""
    Welcome to { TITLE }
    """

    # Collect All Commands
    for active in items:
        if isinstance(active.object, click.core.Group):
            command_sources.append(active.object)
        elif isinstance(active.object, click.core.Command):
            cli.add_command(active.object)

    return click.CommandCollection(name=TITLE, help=help_text, sources=command_sources)


class MyFramework(spoc.Base):
    """My Framework"""

    components: Any
    plugins: Any

    def init(self):
        """Class __init__ Replacement"""
        framework = spoc.init(MODULES)

        # Parts
        self.components = framework.components
        self.plugins = framework.plugins

        # Plugins (Demo)
        for method in framework.plugins.get("on_startup", []):
            method()

        # The (CLI) Command-Line Interface
        self.cli = handle_commands(framework.components.commands.values())

    @staticmethod
    def keys():
        return ("components", "plugins", "cli")

```
