# -*- coding: utf-8 -*-
"""
# Elastic Frameworks

Examples:
    >>> from typing import Any
    >>>
    >>> import spoc
    >>>
    >>> PLUGINS = ["models", "views"]
    >>>
    >>> class MyFramework(spoc.Base):
    >>>     components: Any
    >>>     extras: Any
    >>>     keys: Any
    >>>
    >>>     def init(self):
    >>>         # __init__ Replacement
    >>>         app = spoc.init(PLUGINS)
    >>>
    >>>         self.components = app.components
    >>>         self.extras = app.extras
    >>>
    >>>         self.keys = [
    >>>             "component",
    >>>             "extras",
    >>>         ]
"""

from .installer import start_project
from .singleton import Singleton as Base
from .workers import BaseProcess, BaseServer, BaseThread

try:
    # Core Tools
    from .components import component, is_component

    # Frame Work
    from .framework import Spoc, init
    from .importer import frozendict
    from .importer.base import search_method as search
    from .importer.tools import get_fields

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
    "start_project",
    "component",
    "frozendict",
    "get_fields",
    "is_component",
    "search",
)
