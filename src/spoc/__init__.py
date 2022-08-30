"""
    Module(INIT)
"""

import pathlib

from .framework import framework
from .frozendict import FrozenDict as frozendict
from .plugins import plugin
from .project import project
from .tools import get_attr, get_fields


def root(path):
    """Easy Level-Up Folder(s)."""

    return pathlib.Path(path).parents
