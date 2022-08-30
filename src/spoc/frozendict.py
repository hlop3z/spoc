"""
    Exception & Error Messages
"""


class FrozenDict(dict):
    """Immutable Dictionary"""

    def __setitem__(self, key, value):
        """Set"""
        raise TypeError(
            f"{type(self).__name__} object does not support item assignment"
        )

    def __delitem__(self, key):
        """Delete"""
        raise TypeError(f"{type(self).__name__} object does not support item deletion")

    def __getattribute__(self, attribute):
        """Get Attribute"""
        if attribute in ("clear", "update", "pop", "popitem", "setdefault"):
            raise AttributeError(
                f"{type(self).__name__} object has no attribute {attribute}"
            )
        return dict.__getattribute__(self, attribute)

    def __hash__(self):
        """Hash"""
        return hash(tuple(sorted(self.iteritems())))

    def fromkeys(self, S, v):
        """From-Keys"""
        return type(self)(dict(self).fromkeys(S, v))
