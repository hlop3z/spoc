import dataclasses as dc

from framework.framework import model


@dc.dataclass
@model
class UserAccount:
    id: int
    name: str


@dc.dataclass
@model
class Role:
    id: int
    name: str
