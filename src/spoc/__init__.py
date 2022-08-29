"""
    Module(INIT)
"""

import pathlib

from .framework import framework
from .plugins import plugin
from .project import project


def root(path):
    """Easy Level-Up Folder(s)."""

    return pathlib.Path(path).parents
