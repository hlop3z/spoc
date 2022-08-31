"""
    DataClasses
"""

import dataclasses as dc
import typing


@dc.dataclass(frozen=True)
class Class:
    """Project Classes"""

    name: str = None
    app: str = None
    module: str = None
    key: str = None
    uri: str = None
    cls: typing.Any = None


@dc.dataclass(frozen=True)
class Definition:
    """Project Definitions"""

    path: str
    app: str
    module: str
    fields: dict[str, typing.Any]


@dc.dataclass(frozen=True)
class API:
    """Project API"""

    modules: dict
    plugins: dict


@dc.dataclass(frozen=True)
class Component:
    """Project Plugin"""

    config: typing.Any = None
    metadata: typing.Any = None
    is_spoc_plugin: bool = True


@dc.dataclass(frozen=True)
class Global:
    """Project Globals"""

    schema: typing.Any = None
    modules: typing.Any = None


@dc.dataclass(frozen=True)
class Project:
    """Project Core"""

    keys: typing.Any
    modules: typing.Any
    schema: typing.Any
    components: typing.Any
    settings: typing.Any
    installed_apps: list[str]
    toml: typing.Any
    pyproject: typing.Any
