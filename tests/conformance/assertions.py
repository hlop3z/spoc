"""Static assertions over the generated stub, read by mypy, pyright, and ty.

Nothing here runs meaningfully — `assert_type` is a no-op at runtime. The file
exists to be *type checked*: each assertion states the type a developer gets
from the editor, so a stub that silently stopped delivering it fails the build
instead of quietly degrading to `Any`.

Three checkers read this file. `ty` is the project's own gate but is beta and
runs in nobody's editor; pyright is what VS Code runs through Pylance, which
makes it the authority on the autocomplete claim; mypy is the independent third
reading. A disagreement between them is a finding, not something to smooth over.
"""

from collections.abc import Callable
from typing import Any, assert_type

from framework import framework
from apps.shop.models import Product
from apps.shop.resources import SearchIndex

# ── The three shapes resolve to the three static types ────────────────────

# A class is registered as itself, so the record yields the class, not an
# instance of it. This is the distinction a container-style `get(Product)`
# API gets wrong.
assert_type(framework.resolve("models:shop.product").object, type[Product])

# A value yields its own type.
assert_type(framework.resolve("resources:shop.search_index").object, SearchIndex)

# A callable yields its signature, parameters included.
assert_type(
    framework.resolve("views:shop.list_products").object,
    Callable[[], dict[str, int]],
)
assert_type(framework.resolve("views:shop.find_product").object, Callable[[str], str])

# ── Degradation is visible, not disguised ─────────────────────────────────

# An unannotated callable degrades to Any rather than being guessed at.
assert_type(framework.resolve("views:shop.unannotated").object, Callable[..., Any])

# Permissive mode: an identifier the project does not declare still resolves,
# as Any. `--strict` is what turns this line into an error instead.
assert_type(framework.resolve("models:shop.nonexistent").object, Any)

# ── What the developer actually does with the result ──────────────────────
#
# The assertions above prove the stub's types; these prove they are *usable* —
# construct the class, call the callable, read a member off the value. This is
# the chain that has to hold for editor completion to be real.

product_cls = framework.resolve("models:shop.product").object
product = product_cls(id=1, name="mouse", price_cents=2900)
assert_type(product.price_cents, int)
assert_type(product.name, str)

lister = framework.resolve("views:shop.list_products").object
assert_type(lister(), dict[str, int])

finder = framework.resolve("views:shop.find_product").object
assert_type(finder("mouse"), str)

index = framework.resolve("resources:shop.search_index").object
assert_type(index.lookup("mouse"), str)

# ── The same registry, navigated instead of spelled ───────────────────────
#
# `objects.<kind>.<namespace>.<object_name>` is the identifier's own facets as
# members. The types must be identical to the ones above — a second route to a
# component that described it differently would be worse than no second route.

assert_type(framework.objects.models.shop.product.object, type[Product])
assert_type(framework.objects.resources.shop.search_index.object, SearchIndex)
assert_type(
    framework.objects.views.shop.list_products.object, Callable[[], dict[str, int]]
)
assert_type(framework.objects.views.shop.find_product.object, Callable[[str], str])

# Degradation stays honest by this route too.
assert_type(framework.objects.views.shop.unannotated.object, Callable[..., Any])

# And the result is usable, not merely typed.
navigated = framework.objects.models.shop.product.object(
    id=2, name="keyboard", price_cents=4500
)
assert_type(navigated.price_cents, int)
assert_type(framework.objects.views.shop.list_products.object(), dict[str, int])
