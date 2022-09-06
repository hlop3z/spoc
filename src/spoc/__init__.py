"""
    Module(INIT)
"""

import pathlib

from .components import component
from .framework import MODE as mode
from .framework import TOML_DIR as config
from .framework import framework
from .frozendict import FrozenDict as frozendict
from .imports import search_method as search
from .project_core import project
from .singleton import singleton
from .tools import get_attr, get_fields

settings = project.settings


def find_root(path):
    """Easy Level-Up Folder(s)."""

    return pathlib.Path(path).parents
