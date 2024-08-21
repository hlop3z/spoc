"""
Components
"""

from typing import Any
import spoc


components = spoc.Components()
components.add("command", {"is_click": True})


# Class @Decorator
def commands(obj: Any = None):
    """Demo"""
    components.register("command", obj)
    return obj
