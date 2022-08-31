"""
    Components
"""
import functools

from .types import Component


# Function
def component(
    cls: object = None,
    *,
    config: dict = None,
    metadata: dict = None,
):
    """Plugin Creator"""
    config = config or {}
    metadata = metadata or {}
    if cls is None:
        return functools.partial(
            component,
            config=config,
            metadata=metadata,
        )

    # Real Wrapper
    cls.__spoc__ = Component(config=config, metadata=metadata)
    return cls
