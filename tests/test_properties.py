"""
Property-based tests (specs: object-identity, component-registry).

Universal quantification over the two hardest contracts: the identifier
grammar (round-trip identity, rejection completeness) and the registry's
invariants under arbitrary operation sequences and thread interleavings.
Example-based tests state the cases we thought of; these hunt for the ones
we didn't. Budgets are stated per test so `task check` stays fast.
"""

import re
from concurrent.futures import ThreadPoolExecutor

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from spoc import compose, parse
from spoc.core.exceptions import (
    DuplicateComponentError,
    IdentityDivergenceError,
    InvalidSegmentError,
    MalformedIdentifierError,
)
from spoc.core.identity import SEGMENT_PATTERN
from spoc.core.registry import Registry

# ── Generators ────────────────────────────────────────────────────────────

#: Conforming segments, straight from the grammar the spec states.
segments = st.from_regex(SEGMENT_PATTERN, fullmatch=True)

#: Well-formed identifiers.
identifiers = st.builds(compose, segments, segments, segments)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


def _mutate(identifier: str, index: int, junk: str) -> str:
    """Splice arbitrary junk into a valid identifier."""
    cut = index % (len(identifier) + 1)
    return identifier[:cut] + junk + identifier[cut:]


#: Non-conforming inputs: mutated valid identifiers plus arbitrary text,
#: filtered against the full-identifier regex — the regex is the single
#: source of truth for what "conforming" means, so any disagreement between
#: it and the implementation surfaces as a counterexample.
malformed = st.one_of(
    st.builds(
        _mutate,
        identifiers,
        st.integers(min_value=0),
        st.sampled_from([":", ".", " ", "A", "-", "é", "\x00", "9", "_", ""]),
    ),
    st.text(max_size=30),
).filter(lambda s: not _IDENTIFIER_RE.match(s))

# ── Grammar: round-trip and rejection completeness ────────────────────────


@settings(max_examples=500)
@given(kind=segments, namespace=segments, object_name=segments)
def test_compose_parse_round_trip_is_identity(kind, namespace, object_name):
    """Spec: round-trip identity over the whole grammar."""
    parsed = parse(compose(kind, namespace, object_name))
    assert (parsed.kind, parsed.namespace, parsed.object_name) == (
        kind,
        namespace,
        object_name,
    )


@settings(max_examples=500)
@given(text=malformed)
def test_rejection_is_complete_over_the_input_space(text):
    """Spec: no non-conforming input is accepted, converted, or partially
    parsed — refusal is always one of the grammar's own typed errors."""
    try:
        parse(text)
    except (MalformedIdentifierError, InvalidSegmentError):
        return
    raise AssertionError(f"non-conforming input was accepted: {text!r}")


@settings(max_examples=300)
@given(junk=st.text(max_size=20).filter(lambda s: not SEGMENT_PATTERN.match(s)))
def test_segment_rejection_never_converts(junk):
    """A stated non-conforming segment is refused, never coerced (spec:
    stated names verbatim)."""
    try:
        compose("models", "blog", junk)
    except InvalidSegmentError as exc:
        assert "object_name" in str(exc)
        return
    raise AssertionError(f"non-conforming segment was accepted: {junk!r}")


# ── Registry: invariants under arbitrary operation sequences ──────────────


class RegistryMachine(RuleBasedStateMachine):
    """Arbitrary register/resolve/enumerate sequences against a shadow model.

    The model is a plain dict identifier→object; every rule asserts the
    registry and the model never disagree, and refusals are the exact typed
    errors the spec names.
    """

    def __init__(self):
        super().__init__()
        self.registry = Registry(("models", "views"))
        self.model: dict[str, object] = {}
        self.objects: list[object] = []

    @rule(
        kind=st.sampled_from(["models", "views"]),
        namespace=st.sampled_from(["alpha", "beta"]),
        object_name=st.sampled_from(["one", "two", "three"]),
        reuse=st.booleans(),
    )
    def register(self, kind, namespace, object_name, reuse):
        identifier = f"{kind}:{namespace}.{object_name}"
        # Sometimes re-register an existing object to probe idempotence and
        # divergence; otherwise a fresh unique object.
        obj = (
            self.objects[len(identifier) % len(self.objects)]
            if reuse and self.objects
            else type("Obj", (), {})()
        )
        prior_identity = self.registry.identifier_of(obj)
        try:
            record = self.registry.add(kind, namespace, object_name, obj)
        except DuplicateComponentError:
            # Refusal is correct only if the slot is truly taken by another.
            assert identifier in self.model and self.model[identifier] is not obj
        except IdentityDivergenceError:
            # Refusal is correct only if the object already has another home.
            assert prior_identity is not None and prior_identity != identifier
        else:
            assert record.identifier == identifier
            self.model[identifier] = obj
            if obj not in self.objects:
                self.objects.append(obj)

    @rule()
    def resolve_all_known(self):
        for identifier, obj in self.model.items():
            assert self.registry.resolve(identifier).object is obj

    @invariant()
    def registry_matches_model_exactly(self):
        assert {c.identifier for c in self.registry.all()} == set(self.model)
        assert len(self.registry) == len(self.model)

    @invariant()
    def enumeration_is_deterministic(self):
        first = [c.identifier for c in self.registry.all()]
        second = [c.identifier for c in self.registry.all()]
        assert first == second


TestRegistryInvariants = RegistryMachine.TestCase
TestRegistryInvariants.settings = settings(max_examples=60, stateful_step_count=30)


# ── Concurrency: generated batches with duplicate races ───────────────────


@settings(max_examples=25, deadline=None)
@given(
    names=st.lists(st.sampled_from(["a", "b", "c", "d", "e"]), min_size=2, max_size=24)
)
def test_concurrent_batches_end_consistent(names):
    """Spec: any interleaving — exactly-once presence, one winner per
    identifier, refusals typed. Duplicate names in the batch are deliberate
    duplicate races."""
    registry = Registry(("models",))
    outcomes: list[tuple[str, bool]] = []

    def worker(name: str) -> None:
        try:
            registry.add("models", "race", name, type("Obj", (), {})())
            outcomes.append((name, True))
        except DuplicateComponentError:
            outcomes.append((name, False))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, names))

    # One winner per distinct name, a loser for every duplicate submission.
    assert {c.identifier for c in registry.all()} == {
        f"models:race.{n}" for n in set(names)
    }
    wins = [n for n, ok in outcomes if ok]
    assert sorted(wins) == sorted(set(names))
    assert len(outcomes) == len(names)
