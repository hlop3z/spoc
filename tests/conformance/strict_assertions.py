"""Static assertions valid under a *strict* stub, read by mypy, pyright, and ty.

The permissive assertions include claims strict mode rejects by design (an
undeclared identifier degrading to `Any`), so strict conformance gets its own
file: every claim here is legal under `--strict`, and a checker reporting any
diagnostic on it means the emitted stub itself is defective — the exact failure
mode that shipped when a suppression sat on a line its checker never read.

The consuming file is checked against an ephemerally generated strict stub (see
`strict_project` in ``tests/test_conformance.py``); generation is deterministic,
so the bytes are the ones `spoc stubs --strict` gives a user.
"""

from collections.abc import Callable
from typing import Any, assert_type

from spoc import component

from framework import framework
from apps.shop.models import Product
from apps.shop.resources import SearchIndex, search_index

# ── The three shapes resolve to the three static types ────────────────────

assert_type(framework.resolve("models:shop.product").object, type[Product])
assert_type(framework.resolve("resources:shop.search_index").object, SearchIndex)
assert_type(
    framework.resolve("views:shop.list_products").object,
    Callable[[], dict[str, int]],
)
assert_type(framework.resolve("views:shop.find_product").object, Callable[[str], str])

# ── Degradation is visible, not disguised ─────────────────────────────────

assert_type(framework.resolve("views:shop.unannotated").object, Callable[..., Any])

# ── The results stay usable ───────────────────────────────────────────────

product_cls = framework.resolve("models:shop.product").object
product = product_cls(id=1, name="mouse", price_cents=2900)
assert_type(product.price_cents, int)

lister = framework.resolve("views:shop.list_products").object
assert_type(lister(), dict[str, int])

# ── Navigation is identical in both emission modes ────────────────────────
#
# The tree is emitted the same way strict or permissive: an undeclared member
# is an error because it is absent, not because an overload was withheld.

assert_type(framework.objects.models.shop.product.object, type[Product])
assert_type(framework.objects.resources.shop.search_index.object, SearchIndex)
assert_type(framework.objects.views.shop.unannotated.object, Callable[..., Any])

# ── The low-level marker preserves what it marks ──────────────────────────
#
# `component()` is public, so a checker reading its call site must see the
# object's own type — the same contract the kind handles hold. Erasing it here
# would make a stub derived from a marked object promise `Any` while every
# runtime assertion about it still passed. Both call forms are claimed: the
# parameterized one that marks and returns, and the bare one that returns a
# decorator which is itself identity.

assert_type(search_index, SearchIndex)


# The bare form is claimed on a function, which is where erasure is observable:
# an `Any`-returning decorator leaves a *class* binding intact under mypy, so a
# decorated class proves nothing here, while a decorated function degrades to
# `Any` and takes this assertion down with it.


@component(kind="views", name="spare_view")
def spare_view(term: str) -> str:
    return term


assert_type(spare_view("term"), str)
