# -*- coding: utf-8 -*-

"""
Object-Class Tools
"""


def get_fields(model: object):
    """Get Object Fields"""
    return [i for i in dir(model) if not i.startswith("__")]


def get_attr(model: object, name: str):
    """Get Object Attribute IF Exist"""
    if hasattr(model, name):
        return getattr(model, name)
    return None
