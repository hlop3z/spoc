# -*- coding: utf-8 -*-
"""
Auto-Importer
"""

import importlib
import pkgutil
from pkgutil import ModuleInfo
from types import ModuleType
from typing import Any, Iterator

from .frozendict import FrozenDict
from .tools import get_attr, get_fields
from .types import Core, Definition

# from collections.abc import Iterator


def iter_namespace(ns_pkg: ModuleType) -> Iterator[ModuleInfo]:
    """
    Iterate over all modules in a given namespace package.

    Args:
        ns_pkg (module): The namespace package to search for modules.

    Returns:
        Iterator[ModuleInfo]: An iterator over module information in the namespace package.

    Reference:
        https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
    """
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def import_module(single_app: str) -> ModuleType | None:
    """
    Import a single module by name.

    Args:
        single_app (str): The name of the module to import.

    Returns:
        module or None: The imported module if found; otherwise, None.
    """
    try:
        module = importlib.import_module(single_app)
    except Exception:
        module = None
    return module


def import_modules(all_apps: list) -> dict:
    """
    Import multiple modules and discover plugins within them.

    Args:
        all_apps (list): A list of module names to import and search for plugins.

    Returns:
        dict: A dictionary where keys are plugin names and values are the imported plugin modules.

    Reference:
        https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
    """
    installed_apps = {}
    for app in all_apps:
        module = import_module(app)
        if module:
            discovered_plugins = {
                name: importlib.import_module(name)
                for finder, name, ispkg in iter_namespace(module)
            }
            installed_apps.update(discovered_plugins)
    return installed_apps


def get_modules(modules: list, apps: list) -> Core:
    """
    Discover and organize plugins from specified modules and applications.

    Args:
        modules (list): A list of module names to organize.
        apps (list): A list of application names to search for plugins.

    Returns:
        Core: A Core object containing the discovered modules and organized plugins.
    """
    plugin_dict: Any = {key: [] for key in modules}
    installed_apps = import_modules(apps)

    for app_path, module_setup in installed_apps.items():
        uri_parts = app_path.split(".")
        app_name = uri_parts[0]
        app_module = None
        if len(uri_parts) > 1:
            app_module = uri_parts[1]
        if app_module and app_module in modules:
            current_fields = {}
            for field in get_fields(module_setup):
                current_node = get_attr(module_setup, field)
                if current_node is not None:
                    current_fields[field] = current_node
            plugin: Definition = Definition(
                path=app_path,
                app=app_name,
                module=app_module,
                fields=FrozenDict(current_fields),
            )
            plugin_dict[app_module].append(plugin)

    return Core(modules=installed_apps, components=plugin_dict)


def search_object(dotted_path: str) -> Any:
    """
    Search for an `object` within a module using a dotted path notation.

    Args:
        dotted_path (str): The dotted path string representing the `object` location.

    Returns:
        Any: The `object` found at the specified dotted path.

    Example:

    ```python
    spoc.search_object("demo.middleware.on_event")
    ```
    """
    parts = dotted_path.split(".")
    root = parts[0]
    module = import_module(root)
    import_modules([root])
    for part in parts[1:]:
        module = get_attr(module, part)
    return module
