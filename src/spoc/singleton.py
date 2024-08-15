# -*- coding: utf-8 -*-
"""
Tool for Singleton(s)
"""


class Singleton:
    """Class: Create a Singleton"""

    def __new__(cls, *args, **kwargs):
        it_id = "__it__"
        it = cls.__dict__.get(it_id, None)
        if it is not None:
            return it
        it = object.__new__(cls)
        setattr(cls, it_id, it)
        it.init(*args, **kwargs)
        return it

    def init(self, *args, **kwargs):
        """Class __init__ Replacement"""


def singleton(cls):
    """Function: Create a Singleton"""
    custom_class = type(
        cls.__name__,
        (cls, Singleton),
        {},
    )
    return custom_class
