"""
    Elastic Framework Builder
"""

# Core Tools
from .components import component, is_component

# Frame Work
from .framework import Spoc as App
from .importer import frozendict, get_fields, search
from .singleton import singleton

# App
# extras = Spoc.extras
# plugin = Spoc.plugin

# Globals
base_dir = App.base_dir
config = App.config
mode = App.mode
project = App.project
settings = App.settings
