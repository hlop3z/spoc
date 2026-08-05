import dataclasses as dc

from framework.framework import model

# PEP 8 class names convert to their snake_case identifier automatically:
# Product → models:catalog.product.

#: The storefront's stock — in memory on purpose: the reference app is about
#: the kernel, not an ORM. Views in any app reach this *through the
#: registry*, never by importing this module.
PRODUCTS: dict[int, "Product"] = {}


@dc.dataclass
@model
class Product:
    id: int
    name: str
    price_cents: int


def initialize():
    """Module lifecycle: seed the stock when the app loads."""
    PRODUCTS.update(
        {
            1: Product(id=1, name="keyboard", price_cents=7900),
            2: Product(id=2, name="mouse", price_cents=2900),
        }
    )


def teardown():
    PRODUCTS.clear()
