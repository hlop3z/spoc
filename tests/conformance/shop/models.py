"""A constructible component: the registry hands back the class itself."""

import dataclasses as dc

from framework import model


@dc.dataclass
@model
class Product:
    id: int
    name: str
    price_cents: int
