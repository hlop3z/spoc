# -*- coding: utf-8 -*-
"""
# Elastic Frameworks

This example demonstrates how to create a custom framework by extending the `spoc.Base` class.
The framework initializes via `spoc.init` with a list of `modules`,
and it provides access to `components` and `extras`.

Examples:
::

    from typing import Any
    import spoc

    PLUGINS = ["models", "views"]

    class MyFramework(spoc.Base):
        components: Any
        extras: Any
        keys: Any

        def init(self):
            # __init__ Replacement
            app = spoc.init(PLUGINS)

            # Assign components and extras from the initialized app
            self.components = app.components
            self.extras = app.extras

            # Define a list of keys relevant to the framework
            self.keys = [
                "component",
                "extras",
            ]
"""

# Core Tools
from .components import Components, component, is_component

# Import Tools
from .importer import frozendict
from .importer.base import search_method as search
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
    "component",
    "is_component",
    "start_project",
    # Importer
    "get_fields",
    "search",
    "frozendict",
)
