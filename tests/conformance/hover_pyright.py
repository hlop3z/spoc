"""Pyright-only assertions on the *rendered* type — what a hover shows.

`assert_type` proves the type is correct; this proves how it is written out.
That matters because the rendered string is literally what VS Code displays on
hover and what the completion list is built from, and pyright is the engine
Pylance runs. If this file passes, the editor experience is the one the docs
promise.

Read by pyright only. `reveal_type` with an `expected_text` argument is a
pyright extension: mypy and ty see a one-argument builtin and would reject the
second, so the conformance runner points them at ``assertions.py`` instead.
"""

# ruff: noqa: F821  # `reveal_type` is a checker builtin; this file never runs.

from framework import framework

# The class itself, not an instance of it.
reveal_type(  # type: ignore[name-defined]
    framework.resolve("models:shop.product").object,
    expected_text="type[Product]",
)

# A value renders as its own class.
reveal_type(  # type: ignore[name-defined]
    framework.resolve("resources:shop.search_index").object,
    expected_text="SearchIndex",
)

# A callable renders with its full signature — parameters included, which is
# what makes the completion list useful rather than merely present.
reveal_type(  # type: ignore[name-defined]
    framework.resolve("views:shop.find_product").object,
    expected_text="(str) -> str",
)

reveal_type(  # type: ignore[name-defined]
    framework.resolve("views:shop.list_products").object,
    expected_text="() -> dict[str, int]",
)

# Degradation is visible in the hover too, rather than looking like a real type.
reveal_type(  # type: ignore[name-defined]
    framework.resolve("views:shop.unannotated").object,
    expected_text="(...) -> Any",
)

# Members of the constructed object carry through to the hover.
_product = framework.resolve("models:shop.product").object(
    id=1, name="mouse", price_cents=2900
)
reveal_type(_product.price_cents, expected_text="int")  # type: ignore[name-defined]
