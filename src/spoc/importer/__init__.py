# -*- coding: utf-8 -*-

"""
Module (Core)
"""

from typing import Any

from .base import get_modules
from .frozendict import FrozenDict as frozendict
from .get_spoc import get_spoc_components
from .types import App, Core


def global_dict(core: Core) -> dict:
    """Create Global-Dict"""

    all_modules_dir = {}
    for variables in core.components.values():
        for setup in variables:
            base_uri = f"{setup.app}.{setup.module}"
            for key, field in setup.fields.items():
                if not key == "spoc":
                    module_uri = base_uri + f".{key}"
                    all_modules_dir[module_uri] = field
    return frozendict(all_modules_dir)


def create_framework(
    modules: list[str],
    installed_apps: list[str],
    plugins: dict[str, Any] | None = None,
) -> App:
    """Create Framework"""

    core: Core = get_modules(modules, installed_apps)
    components = get_spoc_components(core.components)
    python_modules = global_dict(core)

    return App(
        plugins=plugins,
        modules=python_modules,
        components=components,
    )
