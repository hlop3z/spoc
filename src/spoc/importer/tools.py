# -*- coding: utf-8 -*-

"""
Object-Class Tools
"""

from typing import Any


def get_fields(obj: Any) -> list:
    """
    Retrieve the non-dunder (non-magic) fields of an object.

    Args:
        obj (Any): The object from which to retrieve fields.

    Returns:
        list: A list of attribute names (fields) that do not start with double underscores (`__`).
    """
    return [i for i in dir(obj) if not i.startswith("__")]


def get_attr(obj: Any, name: str) -> Any:
    """
    Retrieve an attribute of an object if it exists.

    Args:
        obj (Any): The object from which to retrieve the attribute.
        name (str): The name of the attribute to retrieve.

    Returns:
        Any: The value of the attribute if it exists; otherwise, `None`.
    """
    if hasattr(obj, name):
        return getattr(obj, name)
    return None
