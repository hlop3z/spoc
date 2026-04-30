# -*- coding: utf-8 -*-
"""
components.py

Provides decorators and utilities for defining, tagging, and validating
"components" within the SPOC framework.

Tested on Python 3.13+.

Usage:
    from spoc.components import component, Components

    @component(config={"foo": "bar"}, metadata={"type": "service"})
    class MyService:
        ...

    components = Components("service", "model")
    @components.register("service")
    class AnotherService:
        ...

This module enables flexible, metadata-driven component registration and discovery.
"""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol, TypeAlias, TypeVar

from .case_style import case_style

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")
ComponentFactory: TypeAlias = Callable[[], T]

T_co = TypeVar("T_co", covariant=True)


@dataclass(frozen=True)
class Internal:
    """
    Holds metadata and configuration for a registered component.

    Attributes:
        config: Component configuration dictionary
        metadata: Component metadata dictionary
    """

    config: dict[str, Any]
    metadata: dict[str, Any]
    app_name: str = ""
    obj_name: str = ""


@dataclass(frozen=True)
class Component:
    """
    Holds metadata and configuration for a registered component and the component
    that uses it.

    Attributes:
        type: Component type identifier
        uri: Unique resource identifier for the component
        app: Application name the component belongs to
        name: Component name
        object: The actual component object
        internal: Internal metadata container
    """

    type: str
    uri: str
    app: str
    name: str
    object: Any
    internal: Internal


class ComponentDecorated(Protocol[T_co]):
    """Protocol for objects decorated with component metadata."""

    __spoc__: Internal

    # The object itself - making the return type a generic parameter
    def __call__(self, *args: Any, **kwargs: Any) -> T_co: ...


_THIS_FILE = os.path.normpath(__file__)
_SKIP_NAMES = frozenset(
    {"obj", "target_obj", "the_object", "cls", "self", "func", "fn"}
)


def _locate_obj(obj: Any) -> tuple[str, str]:
    """Walk the call stack to find the module and variable name for obj.

    Skips frames from this file and generic internal parameter names so we
    always land in the caller's (user) scope.
    """
    for frame_info in inspect.stack():
        if os.path.normpath(frame_info.filename) == _THIS_FILE:
            continue
        f = frame_info.frame
        for ns in (f.f_locals, f.f_globals):
            for k, v in ns.items():
                if v is obj and not k.startswith("_") and k not in _SKIP_NAMES:
                    return f.f_globals.get("__name__", ""), k
    return "", ""


def component(
    obj: Any = None,
    *,
    config: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """
    Mark a class or function as a "component" by attaching ComponentInfo.

    This decorator attaches metadata to an object to identify it as a component
    in the SPOC framework. Can be used as either a simple decorator or a decorator
    factory with parameters.

    Args:
        obj: The object to decorate (when used as @component)
        config: Optional configuration dictionary for the component
        metadata: Optional metadata dictionary for the component

    Returns:
        The decorated object or a decorator function

    Examples:
        >>> @component(config={"key": "value"}, metadata={"type": "command"})
        >>> class MyComponent:
        >>>     pass
        >>>
        >>> # Or as direct call
        >>> my_func = component(my_func, config={"timeout": 30})
    """
    # Create empty dicts for config and metadata if not provided
    cfg = {} if config is None else config
    meta = {} if metadata is None else metadata

    def decorator(target_obj: Any) -> Any:
        raw_name = getattr(target_obj, "__name__", "")
        if raw_name:
            # Class/function: __name__ and __module__ are authoritative
            app_name = getattr(target_obj, "__module__", "").split(".")[0]
            obj_name = raw_name
        else:
            # Instance: __name__ doesn't exist; make it hashable then locate via frames
            if not type(target_obj).__hash__:
                base = type(target_obj)
                target_obj.__class__ = type(
                    base.__name__, (base,), {"__hash__": object.__hash__}
                )
            frame_module, frame_name = _locate_obj(target_obj)
            app_name = frame_module.split(".")[0]
            obj_name = frame_name
        setattr(
            target_obj,
            "__spoc__",
            Internal(config=cfg, metadata=meta, app_name=app_name, obj_name=obj_name),
        )
        return target_obj

    # If used as @component without parentheses
    if obj is not None:
        return decorator(obj)

    # If used as @component() with parentheses
    return decorator


def is_spoc(obj: Any) -> bool:
    """
    Check whether `obj` has been marked as a spoc object.

    Args:
        obj: The object to check

    Returns:
        True if the object has been decorated with the @component decorator
    """
    # Unwrap proxies with `.object` attribute if present
    info = getattr(obj, "__spoc__", None)
    return info is not None


def is_component(obj: Any, metadata: dict[str, Any]) -> bool:
    """
    Check whether `obj` has been marked as a component with the given metadata.

    Args:
        obj: The object to check
        metadata: The metadata to match against

    Returns:
        True if the object has been decorated with matching metadata
    """
    # Unwrap proxies with `.object` attribute if present
    info = getattr(obj, "__spoc__", None)
    return isinstance(info, Internal) and info.metadata == metadata


class Components:
    """
    Registry for named component‐types and their validation logic.

    This class provides a registry for different types of components and
    manages their registration, validation, and metadata handling.

    Examples:
        >>> components = Components("command", "model")
        >>> @components.register("command", config={"foo": "bar"})
        >>> class Cmd:
        >>>     pass
    """

    def __init__(self, *types: str) -> None:
        """
        Initialize a components registry with the specified component types.

        Args:
            *types: Variable number of component type names to register initially
        """
        self._registry: dict[str, dict[str, Any]] = {}

        for t in types:
            self.add_type(t)

    def add_type(self, name: str, default_meta: dict[str, Any] | None = None) -> None:
        """
        Declare a new component type, optionally with default metadata.

        Args:
            name: Name of the component type to add.
            default_meta: Optional default metadata for this component type.
        """
        type_name = name.lower()
        self._registry[type_name] = default_meta.copy() if default_meta else {}

    def register(
        self, type_name: str, obj: Any = None, *, config: dict[str, Any] | None = None
    ) -> Any:
        """
        Decorator to mark something as a component of `type_name`.

        Args:
            type_name: The component type to register as
            obj: Optional object to directly decorate
            config: Optional configuration dictionary for the component

        Returns:
            A decorator function that registers an object as this component type
            or the decorated object if obj is directly provided

        Raises:
            KeyError: If the component type was not previously declared
        """
        name = type_name.lower()
        if name not in self._registry:
            raise KeyError(f"Component type '{type_name}' not declared")

        meta = {"type": name, **self._registry[name]}

        def decorator(target_obj: Any) -> Any:
            if target_obj is None:
                raise ValueError("Cannot register None as a component")

            processed_obj = component(target_obj, config=config, metadata=meta)
            return processed_obj

        # If used as a direct decorator or function call
        if obj is not None:
            return decorator(obj)

        # If used as @register() with parentheses
        return decorator

    def is_spoc(self, obj: Any) -> bool:
        """
        Check whether `obj` has been marked as a spoc object.

        Args:
            obj: The object to check

        Returns:
            True if the object has been decorated with the @component decorator
        """
        return is_spoc(obj)

    def is_component(self, type_name: str, obj: Any) -> bool:
        """
        Validate that `obj` is a component of the declared `type_name`.

        Args:
            type_name: The component type to check against
            obj: The object to validate

        Returns:
            True if the object is a component of the specified type

        Raises:
            KeyError: If the component type was not previously declared
        """
        key = type_name.lower()
        if key not in self._registry:
            raise KeyError(f"Component type '{type_name}' not declared")
        meta = {"type": key, **self._registry[key]}
        return is_component(obj, meta)

    def get_info(self, obj: Any) -> Internal | None:
        """
        Get the Component(Info) for a given object.

        Args:
            obj: The object to get component info for

        Returns:
            Internal metadata object if available, otherwise None
        """
        return getattr(obj, "__spoc__", None)

    def builder(self, the_object: Any) -> Component:
        """
        Build a Component object from a decorated object.

        Args:
            the_object: A component-decorated object

        Returns:
            A Component instance with metadata extracted from the object

        Raises:
            AttributeError: If the object doesn't have required attributes
        """
        app_name = the_object.__module__.split(".")[0]
        obj_name = the_object.__name__
        uri = f"{app_name}_{self.case_style(obj_name, mode='snake')}"
        class_info = self.get_info(the_object)
        if class_info is None:
            raise AttributeError(f"Object {the_object} is not a component")

        component_type = class_info.metadata.get(
            "type", ""
        )  # Default to empty string if not found

        return Component(
            uri=uri,
            app=app_name,
            name=obj_name,
            internal=class_info,
            object=the_object,
            type=component_type,
        )

    @staticmethod
    def case_style(
        text: str,
        mode: Literal["snake", "camel", "pascal", "kebab"] = "snake",
    ) -> str:
        """
        Convert a string to the given case style.

        Args:
            text: The text to convert
            mode: The case style to convert to

        Returns:
            The converted string in the requested case style
        """
        return case_style(text, mode=mode)
