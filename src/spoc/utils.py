# -*- coding: utf-8 -*-
"""
utils.py

Provides utilities for the SPOC framework.
"""
from typing import Any

from .components import Internal


def get_info(obj: Any) -> Internal:
    """
    Get the Component(Info) for a given object.
    """
    return getattr(obj, "__spoc__", Internal({}, {}))
