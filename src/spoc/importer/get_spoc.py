# -*- coding: utf-8 -*-

"""
Spoc Tools
"""

from dataclasses import make_dataclass
from typing import Any

from .frozendict import FrozenDict
from .tools import get_attr
from .types import Object


def get_spoc_components(plugins: dict) -> Any:
    """Collect and organize all components defined in the given plugins.

    This function iterates over the provided plugins dictionary to collect all components marked
    with specific metadata (`__spoc__`) and organizes them into a structured format. The collected
    components are then returned as a dynamically created frozen dataclass.

    Args:
        plugins (dict): A dict where the key is a module name and the value is a list of module
                        objects. Each module object contains fields that are objects potentially
                        marked as SPOC components.

    Returns:
        Any: A dynamically created frozen dataclass (`Components`) containing all the components.
             Each attribute corresponds to a module key in the `plugins` dictionary, and
             each attribute is a `FrozenDict` containing the components for that module.
    """
    out_dict: dict[str, Any] = {}

    for module_key, module_list in plugins.items():
        module_dict = {}

        for current in module_list:
            for current_module, active_class in current.fields.items():
                metadata = get_attr(active_class, "__spoc__")

                # Spoc Plugin(s)
                if metadata and get_attr(metadata, "is_spoc"):
                    module_uri = f"{current.app}.{current_module.lower()}"
                    global_uri = f"{current.module}.{module_uri}"
                    # Create Object
                    module_dict[module_uri] = Object(
                        name=current_module,
                        app=current.app,
                        module=current.module,
                        key=module_uri,
                        uri=global_uri,
                        object=active_class,
                        info=metadata,
                    )
        # FrozenDict
        out_dict[module_key] = FrozenDict(**module_dict)

    # Return Components
    components = make_dataclass("Components", list(out_dict.keys()), frozen=True)
    return components(**out_dict)
