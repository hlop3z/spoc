import dataclasses as dc

from framework import model

# UserAccount → models:auth.user_account, Role → models:auth.role.
# Pass name= only to override the derived identifier.


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
