from .tools import get_attr
from .types import Class


def get_spoc_plugins(plugins: dict) -> dict:
    """Collect All Project Classes"""

    out_dict = {}
    for module_key, module_list in plugins.items():
        out_dict[module_key] = {}
        for current in module_list:
            for current_module, active_class in current.fields.items():
                metadata = get_attr(active_class, "__meta__")
                if metadata:
                    is_spoc_plugin = get_attr(metadata, "is_spoc_plugin")
                    if is_spoc_plugin:
                        module_uri = f"{current.app}.{current_module.lower()}"
                        out_dict[module_key][module_uri] = Class(
                            name=current_module,
                            uri=module_uri,
                            cls=active_class,
                            app=current.app,
                            module=current.module,
                        )

    return out_dict
