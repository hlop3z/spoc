"""
    Components
"""
import spoc

components = {}
components["command"] = {"type": "command"}

# Class @Decorator
def commands(
    cls: object = None,
):
    """Demo"""
    spoc.component(cls, metadata=components["command"])
    return cls