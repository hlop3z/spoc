# -*- coding: utf-8 -*-

"""
Spoc Tools
"""

import dataclasses as dc
from typing import Any

from .frozendict import FrozenDict
from .tools import get_attr
from .types import Object, Spoc


def get_spoc(plugins: dict) -> Spoc:
    """Collect All Project Classes"""

    out_dict: Any = {}
    global_dict = {}
    for module_key, module_list in plugins.items():
        out_dict[module_key] = {}
        for current in module_list:
            for current_module, active_class in current.fields.items():
                metadata = get_attr(active_class, "__spoc__")
                if metadata:
                    is_spoc_plugin = get_attr(metadata, "is_spoc_plugin")
                    if is_spoc_plugin:
                        module_uri = f"{current.app}.{current_module.lower()}"
                        global_uri = f"{current.module}.{module_uri}"
                        # Create Object
                        out_dict[module_key][module_uri] = Object(
                            name=current_module,
                            app=current.app,
                            module=current.module,
                            key=module_uri,
                            uri=global_uri,
                            object=active_class,
                            info=metadata,
                        )
                        global_dict[global_uri] = active_class
        # FrozenDict
        out_dict[module_key] = FrozenDict(**out_dict[module_key])

    # Return Plugin(s) Setup
    dataclass_globals = dc.make_dataclass("Plugin", list(out_dict.keys()), frozen=True)
    app_schema = dataclass_globals(**out_dict)
    return Spoc(schema=app_schema, modules=FrozenDict(**global_dict))
