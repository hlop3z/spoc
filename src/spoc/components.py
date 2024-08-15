# -*- coding: utf-8 -*-
"""
Components
"""

import dataclasses as dc
import functools
import typing


@dc.dataclass(frozen=True)
class Component:
    """Spoc Plugin"""

    config: typing.Any = None
    metadata: typing.Any = None
    is_spoc_plugin: bool = True


def component(
    cls: typing.Any = None,
    *,
    config: dict | None = None,
    metadata: dict | None = None,
) -> typing.Any:
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


def is_component(cls, metadata: dict | None = None):
    """Plugin Validator"""
    return cls.__spoc__.metadata == metadata  # type: ignore
