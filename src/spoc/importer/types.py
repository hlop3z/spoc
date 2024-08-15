# -*- coding: utf-8 -*-

"""
DataClasses

* Class
* Global
* Core
* Definition
* App
"""

import dataclasses as dc
import typing


@dc.dataclass(frozen=True)
class Class:
    """Project Classes"""

    name: str | None = None
    app: str | None = None
    module: str | None = None
    key: str | None = None
    uri: str | None = None
    object: typing.Any = None


@dc.dataclass(frozen=True)
class Spoc:
    """Project Spoc (Globals)"""

    modules: typing.Any = None
    schema: typing.Any = None


@dc.dataclass(frozen=True)
class Core:
    """Project Core"""

    modules: dict
    plugins: dict


@dc.dataclass(frozen=True)
class Definition:
    """Project Definitions"""

    path: str
    app: str
    module: str
    fields: dict[str, typing.Any]


@dc.dataclass(frozen=True)
class App:
    """Project App"""

    plugin: typing.Any
    module: dict[str, typing.Any]
    extras: dict[str, typing.Any] | None = None
