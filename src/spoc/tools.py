# -*- coding: utf-8 -*-
"""
Generic tools for working with Python modules.

This module provides utilities for creating and managing tool functions
that can be registered, discovered, and called dynamically.
"""

import inspect
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, get_type_hints

F = TypeVar("F", bound=Callable[..., Any])


def tool(
    func: Optional[F] = None,
    *,
    category: str = "general",
    description: Optional[str] = None,
) -> Union[F, Callable[[F], F]]:
    """
    Decorator to mark a function as a tool.

    Args:
        func: The function to mark as a tool
        category: The category this tool belongs to (default: "general")
        description: Custom description for the tool (defaults to function docstring)

    Returns:
        The decorated function with tool attributes

    Example:
        @tool
        def my_tool():
            '''This is a tool'''
            return "result"

        @tool(category="math", description="Add two numbers")
        def add(a, b):
            return a + b
    """

    def decorator(fn: F) -> F:
        setattr(fn, "__is_tool__", True)
        setattr(fn, "__tool_category__", category)

        if description:
            setattr(fn, "__tool_description__", description)

        return fn

    if func is None:
        return decorator

    return decorator(func)


def register_tools(module: ModuleType) -> Dict[str, Dict[str, Any]]:
    """
    Find and register all tool functions in a module.

    Args:
        module: The module containing tool functions

    Returns:
        A dictionary mapping tool names to their metadata

    Example:
        import my_tools
        tools_dict = register_tools(my_tools)
    """
    tools_dict = {}

    for name in dir(module):
        if name.startswith("_"):
            continue

        obj = getattr(module, name)

        if not callable(obj) or not hasattr(obj, "__is_tool__"):
            continue

        # Get tool information
        category = getattr(obj, "__tool_category__", "general")
        description = getattr(
            obj, "__tool_description__", obj.__doc__ or f"Tool: {name}"
        )

        # Get parameter information
        sig = inspect.signature(obj)
        params = []

        # Get type hints if available
        type_hints = get_type_hints(obj)
        return_type = type_hints.pop("return", None)

        for param_name, param in sig.parameters.items():
            param_info = {
                "name": param_name,
                "optional": param.default is not param.empty,
            }

            # Add type annotation if available
            if param_name in type_hints:
                param_type = type_hints[param_name]
                # Handle different ways type can be represented
                if hasattr(param_type, "__name__"):
                    param_info["type"] = param_type.__name__
                else:
                    param_info["type"] = str(param_type).replace("typing.", "")

            # Add default value if available
            if param.default is not param.empty:
                param_info["default"] = param.default

            params.append(param_info)

        # Register the tool
        tools_dict[name] = {
            "func": obj,
            "category": category,
            "description": description.strip() if description else "",
            "params": params,
        }

        # Add return type if available
        if return_type:
            if hasattr(return_type, "__name__"):
                tools_dict[name]["return_type"] = return_type.__name__
            else:
                tools_dict[name]["return_type"] = str(return_type).replace(
                    "typing.", ""
                )

    return tools_dict


def get_submodules(module: ModuleType) -> List[str]:
    """
    Get a list of non-private attributes from a module.

    Args:
        module: The module to inspect

    Returns:
        A list of module attribute names that don't start or end with underscore
    """
    return [
        name
        for name in dir(module)
        if not name.startswith("_") and not name.endswith("_")
    ]
