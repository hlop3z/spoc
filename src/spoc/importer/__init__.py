"""
    Module (Core)
"""

from .base import get_plugins
from .base import search_method as search
from .frozendict import FrozenDict as frozendict
from .get_spoc import get_spoc
from .tools import get_attr, get_fields
from .types import App


def global_dict(core) -> dict:
    """Create Global-Dict"""

    all_modules_dir = {}
    for variables in core.plugins.values():
        for setup in variables:
            base_uri = f"{setup.app}.{setup.module}"
            for key, field in setup.fields.items():
                if not key == "spoc":
                    module_uri = base_uri + f".{key}"
                    all_modules_dir[module_uri] = field
    return frozendict(all_modules_dir)


def create_framework(
    plugins: list[str] = None, installed_apps: list[str] = None, extras: dict = None
) -> App:
    """Create Framework"""

    core = get_plugins(plugins, installed_apps)
    spoc = get_spoc(core.plugins)
    python_variables = global_dict(core)
    return App(
        extras=extras,
        plugin=spoc.schema,
        module=python_variables,
    )
