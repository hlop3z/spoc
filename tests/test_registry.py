"""
Tests for the flat registry and resolution
(specs: component-registry, component-resolution).
"""

import pytest

from spoc.core.exceptions import (
    DuplicateComponentError,
    IdentityDivergenceError,
    InvalidSegmentError,
    MalformedIdentifierError,
    UnknownKindError,
    UnknownNamespaceError,
    UnknownObjectError,
)
from spoc.core.registry import Component, Registry


@pytest.fixture
def registry():
    r = Registry(("models", "views"))
    r.add("models", "blog", "post", object(), metadata={"m": 2})
    r.add("models", "blog", "tag", object())
    r.add("models", "shop", "order", object())
    r.add("views", "blog", "list_posts", lambda: "posts")
    return r


class TestStore:
    def test_one_registry_many_facets(self, registry):
        record = registry.resolve("models:blog.post")
        assert record in registry.all()
        assert record in registry.by_kind("models")
        assert record in registry.by_namespace("blog")

    def test_kind_set_closed(self, registry):
        assert registry.kinds == ("models", "views")
        with pytest.raises(UnknownKindError):
            registry.add("commands", "blog", "sync", object())
        # No API exists to extend the kind set at runtime
        assert not hasattr(registry, "add_kind")
        assert not hasattr(registry, "add_type")

    def test_kinds_validated_at_construction(self):
        with pytest.raises(InvalidSegmentError):
            Registry(("Models",))

    def test_records_carry_projection_metadata(self, registry):
        record = registry.resolve("models:blog.post")
        assert record.identifier == "models:blog.post"
        assert (record.kind, record.namespace, record.name) == (
            "models",
            "blog",
            "post",
        )
        assert record.object is not None
        assert record.metadata == {"m": 2}

    def test_no_second_free_form_channel(self, registry):
        """Records carry one metadata channel — the untyped `config` mapping is gone."""
        record = registry.resolve("models:blog.post")
        assert not hasattr(record, "config")
        with pytest.raises(TypeError):
            registry.add("models", "blog", "extra", object(), config={"a": 1})

    def test_duplicate_identifier_rejected(self, registry):
        with pytest.raises(DuplicateComponentError) as exc:
            registry.add("models", "blog", "post", object())
        assert "models:blog.post" in str(exc.value)

    def test_same_object_rediscovered_is_not_duplicate(self):
        r = Registry(("models",))
        obj = object()
        first = r.add("models", "blog", "post", obj)
        second = r.add("models", "blog", "post", obj)
        assert first is second
        assert len(r) == 1

    def test_reregistration_under_another_identity_is_loud(self):
        """The registry never hands back a record whose identity differs from
        what the caller stated — divergence raises, naming both."""
        r = Registry(("models",))
        obj = object()
        r.add("models", "blog", "post", obj)
        with pytest.raises(IdentityDivergenceError) as exc:
            r.add("models", "shop", "post", obj)
        message = str(exc.value)
        assert "models:blog.post" in message
        assert "models:shop.post" in message
        assert len(r) == 1  # the registry is unchanged after the raise
        assert r.identifier_of(obj) == "models:blog.post"

    def test_identifier_of_unregistered_object_is_none(self):
        assert Registry(("models",)).identifier_of(object()) is None

    def test_reregistration_still_validates_its_segments(self):
        """Identity reuse is not a bypass for the grammar every add() answers to."""
        r = Registry(("models",))
        obj = object()
        r.add("models", "blog", "post", obj)
        with pytest.raises(InvalidSegmentError):
            r.add("models", "blog", "Not A Segment", obj)
        with pytest.raises(UnknownKindError):
            r.add("commands", "blog", "post", obj)

    def test_enumeration_deterministic(self, registry):
        first = [c.identifier for c in registry.all()]
        second = [c.identifier for c in registry.all()]
        assert first == second == sorted(first)

    def test_facets_are_derived_views(self, registry):
        assert {c.identifier for c in registry.by_kind("models")} == {
            "models:blog.post",
            "models:blog.tag",
            "models:shop.order",
        }
        assert {c.identifier for c in registry.by_namespace("blog")} == {
            "models:blog.post",
            "models:blog.tag",
            "views:blog.list_posts",
        }
        assert len(registry) == 4

    def test_records_are_frozen(self, registry):
        record = registry.resolve("models:blog.post")
        with pytest.raises(AttributeError):
            record.name = "other"

    def test_component_is_the_record_type(self, registry):
        assert all(isinstance(c, Component) for c in registry)


class TestResolution:
    def test_successful_resolution(self, registry):
        record = registry.resolve("models:blog.post")
        assert record.identifier == "models:blog.post"

    def test_unknown_kind_names_segment_and_candidates(self, registry):
        with pytest.raises(UnknownKindError) as exc:
            registry.resolve("modle:blog.post")
        message = str(exc.value)
        assert "'modle'" in message
        assert "models" in message and "views" in message

    def test_unknown_namespace_names_segment_and_candidates(self, registry):
        with pytest.raises(UnknownNamespaceError) as exc:
            registry.resolve("models:blogg.post")
        message = str(exc.value)
        assert "'blogg'" in message
        assert "blog" in message and "shop" in message

    def test_unknown_object_names_segment_and_candidates(self, registry):
        with pytest.raises(UnknownObjectError) as exc:
            registry.resolve("models:blog.pots")
        message = str(exc.value)
        assert "'pots'" in message
        assert "post" in message and "tag" in message

    def test_malformed_identifier_describes_grammar(self, registry):
        with pytest.raises(MalformedIdentifierError) as exc:
            registry.resolve("not-an-identifier")
        assert "kind:namespace.object_name" in str(exc.value)

    def test_operation_suffix_rejected(self, registry):
        with pytest.raises(MalformedIdentifierError):
            registry.resolve("models:blog.post.create")

    def test_resolution_never_executes(self, registry):
        """The resolved callable comes back unexecuted."""
        record = registry.resolve("views:blog.list_posts")
        assert callable(record.object)
        assert record.object() == "posts"  # only *we* call it, resolve didn't

    def test_resolution_order_kind_before_namespace(self):
        """An identifier wrong in every segment fails on kind first."""
        r = Registry(("models",))
        with pytest.raises(UnknownKindError):
            r.resolve("nope:nowhere.nothing")
