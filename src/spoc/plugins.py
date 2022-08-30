"""
    Plugins
"""
import functools

from .types import Plugin


# Function
def plugin(
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
            plugin,
            config=config,
            metadata=metadata,
        )

    # Real Wrapper
    cls.__spoc__ = Plugin(config=config, metadata=metadata)
    return cls
