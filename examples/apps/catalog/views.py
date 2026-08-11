import dataclasses as dc

from framework import framework, view

from .models import PRODUCTS


@view
def list_products():
    return {"products": [dc.asdict(p) for p in PRODUCTS.values()]}


@view
def find_product(name: str = "keyboard"):
    """Resolve the live resource mid-call — never at import, when it isn't
    open yet. The registry hands back the same instance the startup hook
    opened; after shutdown this resolution fails loudly instead."""
    index = framework.resolve("resources:catalog.search_index").object
    product_id = index.lookup(name)
    product = PRODUCTS.get(product_id)
    return {"query": name, "product": dc.asdict(product) if product else None}
