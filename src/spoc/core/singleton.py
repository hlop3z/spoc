"""
Singleton pattern implementation.

This module provides two ways to implement the Singleton pattern:
1. A metaclass that can be used to create Singleton classes
2. A decorator that can be applied to existing classes

Usage:
    from spoc.core.singleton import SingletonMeta, singleton

    # Using the metaclass
    class MySingleton(metaclass=SingletonMeta):
        ...

    # Using the decorator
    @singleton
    class MyOtherSingleton:
        ...

Use the metaclass for inheritance-based singletons,
and the decorator for a more flexible, functional approach.
"""

import threading
from functools import wraps
from typing import Any, Callable, Type, TypeVar, cast

# from collections.abc import Callable
# from typing import TypedDict, Unpack


T = TypeVar("T")


class SingletonMeta(type):
    """
    Metaclass that creates a Singleton class.

    Any class using this metaclass will have only one instance, with
    subsequent instantiations returning the same instance.

    Example:

    ```python
    class SingletonClass(metaclass=SingletonMeta):
        def __init__(self, value=None):
            self.value = value or "default"
    ```
    """

    _instances: dict[type, Any] = {}
    _lock = threading.RLock()

    @classmethod
    def reset(mcs, target_cls: type | None = None) -> None:
        """
        Reset the singleton instance(s).

        Args:
            target_cls: A specific class to reset. If None, resets all instances.

        This method is particularly useful for testing scenarios.
        """
        with mcs._lock:
            if target_cls is not None and target_cls in mcs._instances:
                del mcs._instances[target_cls]
            elif target_cls is None:
                mcs._instances.clear()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """
        Creates a new instance or returns an existing one.

        Args:
            *args: Positional arguments to pass to the constructor.
            **kwargs: Keyword arguments to pass to the constructor.

        Returns:
            The singleton instance of the class.
        """
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def singleton(cls: Type[T]) -> Callable[..., T]:
    """
    Decorator to convert a class into a Singleton.

    Args:
        cls: The class to convert to a Singleton.

    Returns:
        A wrapped function that returns the singleton instance.

    Example:

    ```python
    @singleton
    class SingletonClass:
        def __init__(self, value=None):
            self.value = value or "default"
    ```
    """
    instances: dict[type, Any] = {}
    lock = threading.RLock()

    @wraps(cls)
    def get_instance(*args: Any, **kwargs: Any) -> T:
        """
        Get or create the singleton instance.

        Args:
            *args: Positional arguments to pass to the constructor.
            **kwargs: Keyword arguments to pass to the constructor.

        Returns:
            The singleton instance.
        """
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
        return cast(T, instances[cls])

    # Add a reset method to the wrapper function for testing
    def reset() -> None:
        """Reset the singleton instance for testing purposes."""
        with lock:
            if cls in instances:
                del instances[cls]

    get_instance.reset = reset  # type: ignore

    return get_instance
