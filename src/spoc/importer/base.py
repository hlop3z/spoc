# -*- coding: utf-8 -*-
"""
Auto-Importer
"""

import importlib
import pkgutil
from typing import Any

from .frozendict import FrozenDict
from .tools import get_attr, get_fields
from .types import Core, Definition


def iter_namespace(ns_pkg):
    """https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/"""
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def import_module(single_app: str):
    """Import Single-Module"""
    try:
        module = importlib.import_module(single_app)
    except Exception:
        module = None
    return module


def import_modules(all_apps: list) -> dict:
    """https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/"""
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


def get_plugins(plugins: list, apps: list) -> Core:
    """Plugins: Creating & Discovering"""

    plugin_dict: Any = {key: [] for key in plugins}
    installed_apps = import_modules(apps)

    for app_path, module_setup in installed_apps.items():
        uri_parts = app_path.split(".")
        app_name = uri_parts[0]
        app_module = None
        if len(uri_parts) > 1:
            app_module = uri_parts[1]
        if app_module and app_module in plugins:
            current_fields = {}
            for field in get_fields(module_setup):
                current_node = get_attr(module_setup, field)
                if current_node is not None:
                    current_fields[field] = current_node
            plugin = Definition(
                path=app_path,
                app=app_name,
                module=app_module,
                fields=FrozenDict(current_fields),
            )
            plugin_dict[app_module].append(plugin)

    return Core(modules=installed_apps, plugins=plugin_dict)


def search_method(dotted_path: str):
    """Search for Method in <Module>"""
    parts = dotted_path.split(".")
    root = parts[0]
    module = import_module(root)
    import_modules([root])
    for part in parts[1:]:
        module = get_attr(module, part)
    return module
