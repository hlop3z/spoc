"""
Navigating the registry by grammar segment — one test per spec scenario in
typed-registry-navigation's runtime requirements, plus the reflection surface an
editor and a human read.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from spoc.core.exceptions import (
    FrameworkTransitioningError,
    UnknownKindError,
    UnknownNamespaceError,
    UnknownObjectError,
)
from spoc.testing import ProjectTree

MODELS = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Product:
        price_cents = 2900

    @component(kind="models")
    class Invoice:
        total = 1
"""

VIEWS = """
    from spoc.core.declaration import component

    EFFECTS = []

    @component(kind="views")
    def list_products() -> dict[str, int]:
        EFFECTS.append("called")
        return {"count": 1}
"""

FRAMEWORK = """
    import spoc

    framework = spoc.Framework(
        spoc.KindSpec("models", required=False),
        spoc.KindSpec("views", required=False),
    )
"""


def project(tmp_path: Path, *, apps: dict | None = None, framework: str = FRAMEWORK):
    """A started framework and its base directory."""
    tree = ProjectTree(
        apps=apps or {"shop": {"models": MODELS, "views": VIEWS}},
        config={"apps": {"development": list((apps or {"shop": {}}).keys())}},
    ).build(tmp_path, "proj")
    (tree / "framework.py").write_text(textwrap.dedent(framework), encoding="utf-8")
    return tree


@pytest.fixture
def started(tmp_path):
    """A booted framework, reached through its own composition root."""
    base = project(tmp_path)
    import sys

    from spoc.testing import import_state

    with import_state():
        sys.path.insert(0, str(base))
        import framework as root

        root.framework.start(base)
        yield root.framework


# ── Reachability ──────────────────────────────────────────────────────────


def test_every_registered_component_is_reachable(started):
    """One path per component, and the path is the identifier's own facets."""
    reached = {
        started.objects.models.shop.product.identifier,
        started.objects.models.shop.invoice.identifier,
        started.objects.views.shop.list_products.identifier,
    }
    assert reached == {c.identifier for c in started.registry.all()}


def test_the_path_is_the_identifier_respelled(started):
    component = started.objects.models.shop.product
    assert component.identifier == "models:shop.product"
    assert (component.kind, component.namespace, component.object_name) == (
        "models",
        "shop",
        "product",
    )


def test_nothing_is_declared_twice(started):
    """Registration is the only declaration — navigation needs no annotation."""
    assert started.objects.models.shop.product.object.__name__ == "Product"


def test_an_unregistered_component_has_no_path(started):
    with pytest.raises(UnknownObjectError):
        _ = started.objects.models.shop.nonexistent


# ── Pure lookup ───────────────────────────────────────────────────────────


def test_navigation_yields_the_identical_record(started):
    assert started.objects.models.shop.product is started.resolve("models:shop.product")


def test_a_callable_component_is_not_invoked(started):
    """The kernel describes; it never calls what it hands back."""
    import sys

    module = sys.modules["shop.views"]
    before = list(module.EFFECTS)

    component = started.objects.views.shop.list_products

    assert callable(component.object)
    assert list(module.EFFECTS) == before


def test_navigation_is_refused_during_a_transition(started):
    """Same read-consistency rule as resolve: outside an in-flight transition,
    the registry is half-built and answering would be a lie."""
    import threading

    base = started.base_dir
    refused: list[bool] = []

    @started.on_ready
    def _(registry):
        def outsider():
            try:
                _ = started.objects
                refused.append(False)
            except FrameworkTransitioningError:
                refused.append(True)

        thread = threading.Thread(target=outsider)
        thread.start()
        thread.join()

    started.shutdown()
    started.start(base)
    assert refused == [True], "a read from outside the transition must be refused"


# ── Failure precision ─────────────────────────────────────────────────────


def test_unknown_kind_names_the_declared_set(started):
    with pytest.raises(UnknownKindError) as caught:
        _ = started.objects.modles
    assert "modles" in str(caught.value)
    assert "models" in str(caught.value)


def test_unknown_namespace_names_the_candidates(started):
    with pytest.raises(UnknownNamespaceError) as caught:
        _ = started.objects.models.shpo
    assert "shpo" in str(caught.value)
    assert "shop" in str(caught.value)


def test_unknown_object_names_the_candidates(started):
    with pytest.raises(UnknownObjectError) as caught:
        _ = started.objects.models.shop.prodcut
    assert "prodcut" in str(caught.value)
    assert "product" in str(caught.value)


def test_failures_match_identifier_resolution(started):
    """Same mistake, two routes, one answer."""
    with pytest.raises(UnknownObjectError) as by_path:
        _ = started.objects.models.shop.prodcut
    with pytest.raises(UnknownObjectError) as by_identifier:
        started.resolve("models:shop.prodcut")
    assert str(by_path.value) == str(by_identifier.value)


# ── Reserved words ────────────────────────────────────────────────────────

KEYWORD_KIND = """
    from spoc.core.declaration import component

    @component(kind="class")
    class Seminar:
        pass
"""

KEYWORD_FRAMEWORK = """
    import spoc

    framework = spoc.Framework(spoc.KindSpec("class", required=False))
"""


def test_a_reserved_word_segment_is_navigable_with_an_escape(tmp_path):
    """`class` is not spellable as an attribute; `class_` is, and the
    identifier keeps the unescaped name."""
    base = project(
        tmp_path,
        apps={"school": {"class": KEYWORD_KIND}},
        framework=KEYWORD_FRAMEWORK,
    )
    import sys

    from spoc.testing import import_state

    with import_state():
        sys.path.insert(0, str(base))
        import framework as root

        root.framework.start(base)

        component = root.framework.objects.class_.school.seminar
        assert component.identifier == "class:school.seminar"
        assert "class_" in dir(root.framework.objects)


# ── Reflection ────────────────────────────────────────────────────────────


def test_dir_offers_each_level(started):
    assert dir(started.objects) == ["models", "views"]
    assert dir(started.objects.models) == ["shop"]
    assert dir(started.objects.models.shop) == ["invoice", "product"]


def test_repr_says_where_it_is_and_what_it_offers(started):
    assert "models" in repr(started.objects.models)
    assert "2" in repr(started.objects.models.shop)


def test_dunder_probes_are_refused(started):
    """A protocol probe must not be answered with a registry lookup — the
    surface would claim support it does not have."""
    assert not hasattr(started.objects, "__len__")
    assert not hasattr(started.objects, "__iter__")


def test_navigation_reflects_a_later_registration(started):
    """Nothing is materialized, so the walk cannot go stale."""
    assert "late" not in dir(started.objects.models.shop)
    started.registry.add("models", "shop", "late", object())
    assert "late" in dir(started.objects.models.shop)


def test_the_navigator_is_not_shared_state(started):
    """Each access returns a fresh walk over the same registry."""
    assert started.objects is not started.objects
    assert started.objects.models.shop.product is started.objects.models.shop.product
