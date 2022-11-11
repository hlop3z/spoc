"""
    Components
"""
import functools

import spoc

COMPONENT = {}
COMPONENT["command"] = {"engine": "my-app-commands", "type": "command"}

# GraphQL Class @Decorator
def command(
    cls: object = None,
):
    """Demo"""
    spoc.component(cls, metadata=COMPONENT["command"])
    return cls