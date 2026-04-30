# -*- coding: utf-8 -*-
"""
types.py

Tested on Python 3.13+.

Provides type aliases for the framework.
"""

from typing import TypeAlias

from .framework import Config as ConfigType
from .components import Internal

Config: TypeAlias = ConfigType
Info: TypeAlias = Internal
