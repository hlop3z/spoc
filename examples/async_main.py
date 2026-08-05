"""
The asynchronous lifecycle over the same storefront apps.

A declaration whose hooks are coroutine functions is async-only: the
synchronous path refuses coroutines loudly rather than guessing at an event
loop, so a project picks its lifecycle path when it declares. This file is
the async variant of ``framework/framework.py`` — a process runs one
declaration or the other, never both.

One consequence worth reading twice: app code that resolves other apps at
call time (``orders.views.order_summary``) binds to the project's one
declaration module, so it belongs to the sync variant's process. Here the
*surface* does the cross-namespace resolution instead — which is the
idiomatic place for it anyway: surfaces enumerate and resolve; apps mostly
just declare.

Run:  uv run python examples/async_main.py
"""

import asyncio
import dataclasses as dc
from pathlib import Path

import spoc

BASE_DIR = Path(__file__).resolve().parent


async def warm_up(objects) -> None:
    # Stands in for real async work: opening pools, priming caches.
    await asyncio.sleep(0)
    print(f"warm_up awaited over {len(objects)} models")


async def drain(objects) -> None:
    await asyncio.sleep(0)
    print("drain awaited")


framework = spoc.Framework(
    spoc.KindSpec("models", on_startup=warm_up, on_shutdown=drain),
    spoc.KindSpec("views", depends_on=("models",)),
    spoc.KindSpec("middleware", required=False),
    spoc.KindSpec("hooks", required=False),
)


async def main() -> None:
    await framework.astart(BASE_DIR)

    # Cross-namespace, done by the surface: resolve catalog's model and view
    # by canonical identifier and compose them here.
    product_cls = framework.resolve("models:catalog.product").object
    stock = framework.resolve("views:catalog.list_products").object()
    cheapest = min(
        (product_cls(**entry) for entry in stock["products"]),
        key=lambda p: p.price_cents,
    )
    print("cheapest product:", dc.asdict(cheapest))

    await framework.ashutdown()


if __name__ == "__main__":
    asyncio.run(main())
