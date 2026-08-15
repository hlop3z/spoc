"""
Tests for the flat registry and resolution
(specs: component-registry, component-resolution).
"""

import ast
import time
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

import pytest

import spoc.core.registry as registry_module
from spoc.core.exceptions import (
    DuplicateComponentError,
    IdentityDivergenceError,
    InvalidSegmentError,
    MalformedIdentifierError,
    UnknownKindError,
    UnknownNamespaceError,
    UnknownObjectError,
)
from spoc.core.navigation import navigator
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
        assert (record.kind, record.namespace, record.object_name) == (
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
            record.object_name = "other"

    def test_component_is_the_record_type(self, registry):
        assert all(isinstance(c, Component) for c in registry)


class TestRecordTypeDescription:
    """A record admits a description of its object's type without that
    description constraining anything at runtime (spec: component-registry —
    records carry projection-sufficient metadata)."""

    def test_undescribed_record_is_unconstrained(self):
        for obj in (object(), "a string", 42, lambda: None, type("K", (), {})):
            record = Component(
                identifier="models:blog.post",
                kind="models",
                namespace="blog",
                object_name="post",
                object=obj,
            )
            assert record.object is obj

    def test_registration_hands_back_an_unconstrained_record(self, registry):
        marker = object()
        record = registry.add("models", "blog", "marker", marker)
        assert record.object is marker

    def test_described_record_carries_the_object_unchanged(self):
        marker = object()
        record: Component[object] = Component(
            identifier="models:blog.post",
            kind="models",
            namespace="blog",
            object_name="post",
            object=marker,
        )
        assert record.object is marker

    def test_description_does_not_alter_runtime_behavior(self):
        marker = object()
        fields = {
            "identifier": "models:blog.post",
            "kind": "models",
            "namespace": "blog",
            "object_name": "post",
            "object": marker,
        }
        undescribed = Component(**fields)
        described = Component[object](**fields)

        assert described == undescribed
        assert type(described) is type(undescribed)
        assert isinstance(described, Component)
        # Indirect so the assignment is a runtime question, which is the point:
        # frozen-ness must hold for a described record exactly as it does today.
        attr = "object_name"
        for record in (described, undescribed):
            with pytest.raises(AttributeError):
                setattr(record, attr, "other")

    def test_the_class_itself_is_the_isinstance_target(self, registry):
        # A parameterized alias is for readers; isinstance still takes the class.
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


class TestSharedValueIdentity:
    """Divergence is a claim about objects, not about equal values.

    The divergence map is keyed by `id()`, which the runtime is free to share
    for small integers, interned strings, and `()`. Two registrations holding
    equal values are two registrations — never one object claiming two names.
    """

    @pytest.mark.parametrize("value", [7, "shared", b"bytes", (), 2.5, None, True])
    def test_equal_values_register_under_distinct_identifiers(self, value):
        registry = Registry(("models",))
        registry.add("models", "first", "one", value)
        registry.add("models", "second", "two", value)

        assert registry.resolve("models:first.one").object == value
        assert registry.resolve("models:second.two").object == value
        assert len(registry) == 2

    def test_a_shared_value_is_still_idempotent_under_one_identifier(self):
        registry = Registry(("models",))
        first = registry.add("models", "blog", "answer", 42)
        second = registry.add("models", "blog", "answer", 42)
        assert first is second
        assert len(registry) == 1

    def test_a_different_object_under_a_taken_identifier_still_collides(self):
        registry = Registry(("models",))
        registry.add("models", "blog", "answer", 42)
        with pytest.raises(DuplicateComponentError):
            registry.add("models", "blog", "answer", "not the same value")

    def test_identifier_of_is_none_for_shared_values(self):
        """`id()` says nothing about which registration a shared value came from."""
        registry = Registry(("models",))
        registry.add("models", "blog", "answer", 42)
        assert registry.identifier_of(42) is None

    def test_real_objects_still_diverge_loudly(self):
        class Post: ...

        obj = Post()
        registry = Registry(("models",))
        registry.add("models", "blog", "post", obj)
        with pytest.raises(IdentityDivergenceError):
            registry.add("models", "shop", "post", obj)


# ── Reading one facet does not pay for the rest ───────────────────────────


def _build(target_names: int, unrelated: int) -> Registry:
    """A registry holding one target facet plus `unrelated` components elsewhere.

    The filler goes in a *different kind*, so it can never be part of any answer
    the measurements below ask for. Anything it costs a reader is waste.
    """
    registry = Registry(("models", "views"))
    for i in range(target_names):
        registry.add("models", "target", f"obj{i}", object())
    for i in range(unrelated):
        registry.add("views", f"filler{i // 100}", f"obj{i}", object())
    return registry


def _fastest(
    operation: Callable[[], object], rounds: int = 5, calls: int = 20
) -> float:
    """The fastest observed time for `operation`, in seconds per call.

    Minimum rather than mean: a timing sample is the true cost plus scheduler
    noise, which is never negative, so the smallest sample is the closest to
    what the code costs. That is what makes this stable enough to assert on.
    """
    best = float("inf")
    for _ in range(rounds):
        start = time.perf_counter()
        for _ in range(calls):
            operation()
        best = min(best, (time.perf_counter() - start) / calls)
    return best


#: How much unrelated data the loaded registry carries, as a multiple of the
#: facet being read. A reader that scans the whole store pays about this much
#: more; one that reads its facet pays about the same.
_UNRELATED_MULTIPLE = 50

#: The ceiling on that ratio. An order of magnitude below the scan's own factor
#: and an order of magnitude above an indexed read's, so neither machine speed
#: nor scheduler noise decides the outcome — only which implementation is there.
_MAX_RATIO = 5.0

_FACET_NAMES = 200


@pytest.mark.parametrize(
    ("what", "read"),
    [
        ("navigation walk", lambda r: navigator(r).models.target.obj0),
        ("by_kind", lambda r: r.by_kind("models")),
        ("namespaces of a kind", lambda r: r.namespaces("models")),
    ],
)
def test_reading_one_facet_does_not_pay_for_the_rest(what, read):
    """Cost tracks the facet, not the registry (spec: component-registry).

    Both registries answer these reads *identically* — the filler is another
    kind's. So the ratio measures only what the reader touched on the way to the
    same answer, which is the property the spec states and the reason a user can
    trust `objects.a.b.c` to cost what `resolve("a:b.c")` costs.
    """
    light = _build(_FACET_NAMES, 0)
    loaded = _build(_FACET_NAMES, _FACET_NAMES * _UNRELATED_MULTIPLE)

    ratio = _fastest(lambda: read(loaded)) / _fastest(lambda: read(light))

    assert ratio < _MAX_RATIO, (
        f"{what} costs {ratio:.1f}x more with {_UNRELATED_MULTIPLE}x unrelated "
        f"components registered elsewhere — the read is walking the whole "
        f"registry instead of its own facet"
    )


class TestOrderingIsDerivedOnce:
    """Ordering is paid per registration, not per read (spec: component-registry).

    The registry is written once at boot and read for the rest of the process,
    so re-sorting per read charges every reader for a fact that only changes
    when someone registers. These tests pin the cost model the spec states, not
    a timing: they count the derivations rather than measure them, so the
    guarantee holds on a slow machine and a fast one alike.
    """

    @staticmethod
    def _counting_sort(monkeypatch) -> Callable[[], int]:
        """Count orderings performed inside the registry module."""
        calls = 0
        real = sorted

        def counting(*args, **kwargs):
            nonlocal calls
            calls += 1
            return real(*args, **kwargs)

        # The module never defines `sorted`, so it resolves the builtin at call
        # time; a module-global shadows it for exactly the code under test.
        monkeypatch.setattr(registry_module, "sorted", counting, raising=False)
        return lambda: calls

    def test_repeated_enumeration_does_not_re_derive_order(self, registry, monkeypatch):
        derivations = self._counting_sort(monkeypatch)

        reads = [registry.all() for _ in range(5)]

        assert derivations() == 1
        assert all(read == reads[0] for read in reads)
        assert [c.identifier for c in reads[0]] == sorted(
            c.identifier for c in reads[0]
        )

    def test_each_facet_is_derived_once_on_its_own(self, registry, monkeypatch):
        """A cached facet does not answer for a facet nobody has asked about."""
        derivations = self._counting_sort(monkeypatch)

        registry.by_kind("models")
        registry.by_kind("models")
        assert derivations() == 1

        registry.by_kind("views")
        assert derivations() == 2

        registry.by_namespace("blog")
        assert derivations() == 3

    def test_a_registration_between_reads_is_observed(self, registry, monkeypatch):
        before = [c.identifier for c in registry.all()]
        derivations = self._counting_sort(monkeypatch)

        registry.add("models", "blog", "author", object())
        after = [c.identifier for c in registry.all()]

        assert "models:blog.author" not in before
        assert after == sorted([*before, "models:blog.author"])
        assert derivations() == 1, "the read after a registration re-derives once"

    def test_every_facet_reflects_a_registration(self, registry):
        """Invalidation is not per-facet — no reader keeps a pre-registration view."""
        registry.by_kind("models")
        registry.by_namespace("blog")
        registry.all()

        registry.add("models", "blog", "author", object())

        assert "models:blog.author" in {
            c.identifier for c in registry.by_kind("models")
        }
        assert "models:blog.author" in {
            c.identifier for c in registry.by_namespace("blog")
        }
        assert "models:blog.author" in {c.identifier for c in registry.all()}

    def test_an_absent_facet_is_answered_but_not_retained(self, registry):
        """`by_*` takes any string, so misses must not be a memory sink.

        Caching them would let a caller asking about namespaces that do not
        exist grow the registry's memory without registering anything.
        """
        kept = len(registry._ordered_views)

        for i in range(50):
            assert registry.by_namespace(f"absent_{i}") == []
            assert registry.by_kind(f"absent_{i}") == []

        assert len(registry._ordered_views) == kept

    def test_a_facet_that_appears_later_is_answered_from_the_store(self, registry):
        """A miss is not remembered as a miss — registering fills it."""
        assert registry.by_namespace("archive") == []

        registry.add("models", "archive", "snapshot", object())

        assert [c.identifier for c in registry.by_namespace("archive")] == [
            "models:archive.snapshot"
        ]

    def test_a_reader_cannot_edit_what_the_next_reader_sees(self, registry):
        """Caching an ordered view must not hand callers the cache itself."""
        first = registry.all()
        first.clear()

        assert len(registry.all()) == 4
        assert registry.by_kind("models") is not registry.by_kind("models")


class TestOneWriter:
    """The registry has exactly one mutator, and that is checked, not trusted.

    Facet drift is unrepresentable by construction: a facet *is* a
    sub-dictionary of the one store, so there is no second structure to fall out
    of step. The identity map beside it is the exception — it answers the
    inverse question and cannot be read off the store — so the guarantee it
    needs is procedural, and a procedural guarantee is only as good as what
    enforces it. This is what enforces it.
    """

    #: Every attribute holding registry state, mapped to the methods allowed to
    #: write it. A new attribute must join this table, which is the moment to ask
    #: whether it can drift from the store — and to justify any writer beyond
    #: `_admit` rather than widen a shared list and weaken it for everything.
    #:
    #: `_ordered_views` is the one entry with a second writer, because it is the
    #: one entry that is *derived*: it holds no fact the store does not already
    #: hold, so it cannot disagree with the store, only lag it. `_ordered` fills
    #: it and `_admit` empties it, both under the lock, and filling happens in the
    #: same acquisition that reads the store — so a view can never be stored over
    #: an invalidation that overtook it.
    WRITERS: ClassVar[dict[str, set[str]]] = {
        "_components": {"__init__", "_admit"},
        "_count": {"__init__", "_admit"},
        "_identifier_of": {"__init__", "_admit"},
        "_ordered_views": {"__init__", "_admit", "_ordered"},
    }

    #: Every attribute holding registry state.
    STATE: ClassVar[tuple[str, ...]] = tuple(WRITERS)

    def _mutating_methods(self) -> dict[str, set[str]]:
        """Method name → the state attributes it writes, by reading the source."""
        source = Path(registry_module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        registry_class = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "Registry"
        )
        found: dict[str, set[str]] = {}
        for method in registry_class.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            for node in ast.walk(method):
                touched = self._state_written_by(node)
                if touched:
                    found.setdefault(method.name, set()).update(touched)
        return found

    def _state_written_by(self, node: ast.AST) -> set[str]:
        """The state attributes this node writes, if any."""
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AugAssign | ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.Delete):
            targets = list(node.targets)
        elif isinstance(node, ast.Call):
            # `self._components.setdefault(...)` and friends mutate in place.
            attr = node.func
            if isinstance(attr, ast.Attribute) and attr.attr in {
                "setdefault",
                "pop",
                "update",
                "clear",
            }:
                targets = [attr.value]
        return {name for target in targets for name in self._state_reached(target)}

    def _state_reached(self, node: ast.expr) -> set[str]:
        """State attribute names reachable as the root of this expression."""
        while isinstance(node, ast.Subscript | ast.Attribute):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            ):
                return {node.attr} & set(self.STATE)
            node = node.value
        return set()

    def test_every_state_attribute_is_written_in_one_place_only(self):
        writers = self._mutating_methods()
        unexpected = {
            method: sorted(
                attr for attr in attrs if method not in self.WRITERS.get(attr, set())
            )
            for method, attrs in writers.items()
        }
        unexpected = {method: attrs for method, attrs in unexpected.items() if attrs}
        assert not unexpected, (
            f"registry state is written outside its declared writers: {unexpected}. "
            "Authoritative state belongs in `_admit`, so a record cannot become "
            "visible through one read and not another. If this is a deliberate new "
            "writer, it needs its own atomicity argument before this table grows."
        )

    def test_the_declared_state_is_the_real_state(self):
        """The list above cannot silently fall behind the class it describes."""
        actual = {
            name
            for name in vars(Registry(("models",)))
            if name not in {"_kinds", "_lock"}
        }
        assert actual == set(self.STATE), (
            f"registry state changed: {sorted(actual)} != {sorted(self.STATE)} — "
            "add it to STATE and decide whether it can drift from the store"
        )
