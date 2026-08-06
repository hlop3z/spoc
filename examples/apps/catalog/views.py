import dataclasses as dc

from framework import view

from .models import PRODUCTS


@view
def list_products():
    return {"products": [dc.asdict(p) for p in PRODUCTS.values()]}
