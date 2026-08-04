import dataclasses as dc

from framework.framework import model

# PascalCase class names need an explicit conforming name —
# identifiers are never inferred or normalized.


@dc.dataclass
@model(name="user_account")
class UserAccount:
    id: int
    name: str


@dc.dataclass
@model(name="role")
class Role:
    id: int
    name: str
