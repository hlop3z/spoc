# -*- coding: utf-8 -*-
"""
Components

This module provides decorators and utilities for creating and validating
components in the application.
"""

import functools
from typing import Any

from .importer.types import Info


def component(
    obj: Any = None,
    *,
    config: dict | None = None,
    metadata: dict | None = None,
) -> Any:
    """
    Component Creator

    A tool to mark an `object` as a component (`plugin`) with configurations
    and metadata.

    Args:
        obj (Any): The object to be decorated.
        config (dict | None): Configuration options for the component.
        metadata (dict | None): Metadata associated with the component.

    Returns:
        Any: The decorated class, marked as a component.

    Examples:
    ::

        @component(config={"setting": "value"}, metadata={"type": "command"})
        class MyComponent:
            pass

        # OR
        component(MyComponent, config={"setting": "value"}, metadata={"type": "command"})
    """

    config = config or {}
    metadata = metadata or {}
    if obj is None:
        return functools.partial(
            component,
            config=config,
            metadata=metadata,
        )

    # Real Wrapper
    obj.__spoc__ = Info(config=config, metadata=metadata)
    return obj


def is_component(obj: Any, metadata: dict | None = None) -> bool:
    """
    Component Validator.

    Validates whether a given object matches the specified metadata.

    Args:
        obj (Any): The object to validate.
        metadata (dict | None): The metadata to validate against.

    Returns:
        bool:
            `True` if the object metadata matches the provided metadata;
            `False` otherwise.

    Example:
    ::

        if is_component(my_obj, metadata={"type": "command"}):
            print("This is a valid component.")
    """

    item = obj
    if hasattr(obj, "object"):
        item = obj.object
    if not hasattr(item, "__spoc__"):
        return False
    return item.__spoc__.metadata == metadata  # type: ignore


class Components:
    """
    Framework Components

    Example:
    ::

        components = spoc.Components("model", "view")

    """

    def __init__(self, *names: Any) -> None:
        """
        Initialize a Component instance.
        """
        self._components: Any = {}
        for name in names:
            self.add(name)

    def add(self, name: str, metadata: dict | None = None) -> None:
        """
        Add a component with the specified name and optional metadata.

        Example:
        ::

            components = spoc.Components()
            components.add("command", {"is_click": True}) # metadata
        """
        meta = metadata or {}
        self._components[name] = {**meta, "type": name}

    def register(self, name: str, obj: Any, config: dict | None = None) -> None:
        """
        Mark an object as a component using the specified configuration.

        Example:
        ::

            components = spoc.Components("command", "model")

            def my_obj(): pass

            components.register("command", my_obj, config={"setting": "value"})
        """
        component(obj, config=config, metadata=self._components[name])

    def is_component(self, name: str, obj: Any) -> bool:
        """
        Validate if the given object is a component with the specified name.

        Example:
        ::

            components = spoc.Components("command", "model")

            def my_obj(): pass

            if not components.is_component("command", my_obj):
                print("This is not a valid component.")

        """
        return is_component(obj, self._components[name])
