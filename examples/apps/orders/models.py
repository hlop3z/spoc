import dataclasses as dc

from framework.framework import model


@dc.dataclass
@model
class Order:
    id: int
    product_id: int
    quantity: int
