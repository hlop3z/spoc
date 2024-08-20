"""
Components
"""

import spoc

COMPONENTS = {}
COMPONENTS["command"] = {"type": "command"}


# Class @Decorator
def commands(
    cls: object = None,
):
    """Demo"""
    spoc.component(cls, metadata=COMPONENTS["command"])
    return cls
