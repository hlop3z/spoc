"""
    Tool to Singleton
"""


class Singleton:
    """Create a Singleton"""

    def __new__(cls, *args, **kwargs):
        it_id = "__it__"
        it = cls.__dict__.get(it_id, None)
        if it is not None:
            return it
        it = object.__new__(cls)
        setattr(cls, it_id, it)
        it.init(cls, *args, **kwargs)
        return it

    def init(self, *args, **kwargs):
        """Class __init__ Replacement"""
