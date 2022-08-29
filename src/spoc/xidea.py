"""
    DataClasses
"""

from collections import UserDict

from .project import Singleton


class SimpleDict(UserDict):
    """
    Custom Dict
    """

    def __setitem__(self, key, value):
        if key in self.keys():
            raise KeyError(f"{{ {key} }} already exist!")
        super().__setitem__(key, value)


# Test
class API(Singleton):
    """
    API's Dicts
    """

    def init(self):
        keys = [
            # Schemas
            "types",
            "forms",
            "methods",
            "commands",
            # Databases
            "databases",
            "models",
        ]
        for key in keys:
            setattr(self, key, SimpleDict())
