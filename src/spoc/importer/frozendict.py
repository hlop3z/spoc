"""
Exception & Error Messages
"""

from typing import Any

# T = TypeVar("T", bound="FrozenDict")


class FrozenDict(dict):
    """Immutable Dictionary"""

    def fromkeys(self, key, value):  # type:ignore
        """
        Create a new FrozenDict with keys from the given iterable and set to the provided value.
        """
        return type(self)(dict(self).fromkeys(key, value))

    def __getattribute__(self, attribute: Any):
        """
        Prevent modification methods from being accessed.
        """
        if attribute in ("clear", "update", "pop", "popitem", "setdefault"):
            raise AttributeError(
                f"{type(self).__name__} object has no attribute {attribute}"
            )
        return dict.__getattribute__(self, attribute)

    def __setitem__(self, key: Any, value: Any):
        """
        Prevent item assignment.
        """
        raise TypeError(
            f"{type(self).__name__} object does not support item assignment"
        )

    def __delitem__(self, key: Any):
        """
        Prevent item deletion.
        """
        raise TypeError(f"{type(self).__name__} object does not support item deletion")

    def __hash__(self):  # type:ignore
        """
        Compute the hash value of the FrozenDict.
        """
        return hash(tuple(sorted(self.iteritems())))

    def __repr__(self) -> str:
        """
        Return the string representation of the FrozenDict.
        """
        return f"{self.__class__.__name__}({super().__repr__()})"
