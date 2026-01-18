import dataclasses as dc

from framework.framework import model

"""
DEPENDENCIES = []

NAME = "auth.models"

def initialize():
    print(f"Initializing {NAME}")
    return True


def teardown():
    print(f"Tearing down {NAME}")
    return True
"""

# Example module: auth.models


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
