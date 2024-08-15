# -*- coding: utf-8 -*-
"""
Elastic Framework Builder
"""

from .installer import start_project

try:
    # Core Tools
    from .components import component, is_component

    # Frame Work
    from .framework import Spoc as App
    from .importer import frozendict
    from .importer.base import search_method as search
    from .importer.tools import get_fields
    from .singleton import singleton

    # Globals
    base_dir = App.base_dir
    config = App.config
    mode = App.mode
    env = App.environment
    settings = App.settings
except ImportError:
    pass

__all__ = (
    # Tools
    "start_project",
    "component",
    "frozendict",
    "get_fields",
    "is_component",
    "search",
    "singleton",
    # Globals
    "base_dir",
    "config",
    "mode",
    "settings",
)
