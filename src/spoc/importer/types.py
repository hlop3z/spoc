# -*- coding: utf-8 -*-

"""
DataClasses

* Info
* Object
* Global
* Core
* Definition
* App
"""

import dataclasses as dc
import typing


@dc.dataclass(frozen=True)
class Info:
    """Spoc Component Info"""

    config: typing.Any = None
    metadata: typing.Any = None
    is_spoc_plugin: bool = True


@dc.dataclass(frozen=True)
class Object:
    """Framework Object"""

    name: str | None = None
    app: str | None = None
    module: str | None = None
    key: str | None = None
    uri: str | None = None
    object: typing.Any = None
    info: Info | None = None


@dc.dataclass(frozen=True)
class Spoc:
    """Framework Globals"""

    modules: typing.Any = None
    schema: typing.Any = None


@dc.dataclass(frozen=True)
class Core:
    """Framework Core"""

    modules: dict
    plugins: dict


@dc.dataclass(frozen=True)
class Definition:
    """Framework Definitions"""

    path: str
    app: str
    module: str
    fields: dict[str, typing.Any]


@dc.dataclass(frozen=True)
class App:
    """Framework App"""

    plugin: typing.Any
    module: dict[str, typing.Any]
    extras: dict[str, typing.Any] | None = None
