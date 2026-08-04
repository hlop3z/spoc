import dataclasses as dc

from framework.framework import model


@dc.dataclass
@model(name="user_account")
class UserAccount:
    id: int
    name: str
