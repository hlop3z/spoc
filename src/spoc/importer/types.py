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

    name: str = None
    app: str = None
    module: str = None
    key: str = None
    uri: str = None
    cls: typing.Any = None


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
    extras: dict[str, typing.Any]
    # global_dict: dict[str, typing.Any]
    module: dict[str, typing.Any]
