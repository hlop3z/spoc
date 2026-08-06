import dataclasses as dc

from framework import framework, view

from .models import Order

# Cross-namespace, the registry way: orders never imports catalog's modules.
# It resolves catalog's objects by canonical identifier at call time, so the
# only coupling between the two apps is the identifier grammar itself.


@view
def order_summary():
    product_cls = framework.resolve("models:catalog.product").object
    stock = framework.resolve("views:catalog.list_products").object()

    order = Order(id=1, product_id=1, quantity=2)
    product = next(
        product_cls(**entry)
        for entry in stock["products"]
        if entry["id"] == order.product_id
    )
    return {
        "order": dc.asdict(order),
        "product": dc.asdict(product),
        "total_cents": product.price_cents * order.quantity,
    }
