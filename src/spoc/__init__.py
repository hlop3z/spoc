import functools

from .app import Settings as Spoc
from .types import Plugin


# Function
def plugin(
    cls: object = None,
    *,
    config: dict = None,
    metadata: dict = None,
):
    config = config or {}
    metadata = config or {}
    if cls is None:
        return functools.partial(
            plugin,
            config=config,
            metadata=metadata,
        )

    # Real Wrapper
    cls.__meta__ = Plugin(config=config, metadata=metadata)
    return cls
