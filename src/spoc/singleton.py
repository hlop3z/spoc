# -*- coding: utf-8 -*-
"""
Tool for Singleton(s)
"""

from typing import Any


class Singleton:
    """
    A Singleton representing the entire `class`. Ensuring a **single global point of access**.
    """

    init: Any

    def __new__(cls, *args, **kwargs):
        it_id = "__it__"
        it = cls.__dict__.get(it_id, None)
        if it is not None:
            return it
        it = object.__new__(cls)
        setattr(cls, it_id, it)
        it.init(*args, **kwargs)
        return it
