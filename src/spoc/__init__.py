# -*- coding: utf-8 -*-
"""
# Elastic Frameworks

This example demonstrates how to create a custom framework by extending the `spoc.Base` class.
The framework initializes via `spoc.init` with a list of `modules`,
and it provides access to `components` and `plugins`.

Example:

```python
from typing import Any
import spoc

MODULES = ["models", "views"]

class MyFramework(spoc.Base):
    components: Any
    plugins: Any

    def init(self):
        # __init__ Replacement
        app = spoc.init(MODULES)

        # Assign components and plugins from the initialized app
        self.components = app.components
        self.plugins = app.plugins

    @staticmethod
    def keys():
        # Define a list of keys relevant to the framework
        return ("components", "plugins", "cli")
```
"""

# Core Tools
from .components import Components

# Import Tools
from .importer.base import search_object
from .importer.frozendict import FrozenDict as frozendict
from .importer.tools import get_fields
from .installer import start_project
from .singleton import Singleton as Base
from .workers import BaseProcess, BaseServer, BaseThread

try:
    # Frame Work
    from .framework import Spoc, init

    # Globals
    base_dir = Spoc.base_dir
    settings = Spoc.settings
    # config = App.config
    # env = App.environment
    # mode = App.mode

except ImportError:
    pass

# Version
__version__ = "0.2.0"

__all__ = (
    # Globals
    "base_dir",
    "settings",
    # Singleton Base Class
    "init",
    "Base",
    # Workers
    "BaseProcess",
    "BaseThread",
    "BaseServer",
    # Tools
    "Components",
    "start_project",
    # Importer
    "frozendict",
    "get_fields",
    "search_object",
)
