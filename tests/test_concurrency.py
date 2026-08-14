"""
The concurrency contract (specs: component-registry, framework-lifecycle).

Registration is serialized and loses nothing; duplicate and divergence
guarantees hold under any interleaving; lifecycle transitions are mutually
exclusive with exactly one winner.
"""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from spoc import Framework, KindSpec
from spoc.core.exceptions import DuplicateComponentError, SpocError, UnknownObjectError
from spoc.core.registry import Registry
from spoc.testing import ProjectTree
from tests.conftest import MODELS_BODY, make_project

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")

WORKERS = 16


def test_parallel_registration_loses_nothing():
    registry = Registry(("models",))

    def register(i: int):
        return registry.add("models", "app", f"component_{i}", object())

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(register, range(200)))

    assert len(registry) == 200
    names = [c.object_name for c in registry.by_kind("models")]
    assert names == sorted(f"component_{i}" for i in range(200))


def test_racing_duplicates_have_one_winner():
    """Two objects racing the same identifier: one record, one loud loser.

    A barrier releases both threads together, which is what makes this a race
    at all. It previously called ``.result()`` on each submission before
    submitting the next — and ``.result()`` blocks, so the two "racing" threads
    ran to completion in sequence and twenty repetitions exercised nothing the
    sequential duplicate test does not already cover. A concurrency test must
    establish the overlap, never assume it.
    """
    for _ in range(20):  # a race needs repetitions to be a test at all
        registry = Registry(("models",))
        outcomes: list[str] = []
        barrier = threading.Barrier(2)

        def attempt(registry=registry, outcomes=outcomes, barrier=barrier):
            barrier.wait(timeout=5)  # bounded: a broken barrier fails, never hangs
            try:
                registry.add("models", "app", "contested", object())
                outcomes.append("won")
            except DuplicateComponentError:
                outcomes.append("lost")

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt), pool.submit(attempt)]
            for f in futures:
                f.result()

        assert sorted(outcomes) == ["lost", "won"]
        assert len(registry) == 1


def test_reads_concurrent_with_writes_see_only_complete_records():
    registry = Registry(("models",))
    seen_bad = []

    def write():
        for i in range(300):
            registry.add("models", "app", f"c{i}", object())

    def read():
        for _ in range(300):
            for record in registry.all():
                if record.identifier != f"models:app.{record.object_name}":
                    seen_bad.append(record)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(write), pool.submit(read), pool.submit(read)]
        for f in futures:
            f.result()

    assert not seen_bad
    assert len(registry) == 300


class CountingLock:
    """A lock that records how many times it was acquired as a context manager."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.acquisitions = 0

    def __enter__(self):
        self.acquisitions += 1
        return self._lock.__enter__()

    def __exit__(self, *exc_info):
        return self._lock.__exit__(*exc_info)


def test_a_resolution_failure_is_composed_from_one_observation(monkeypatch):
    """The failure path observes the store exactly once.

    Counting acquisitions rather than racing threads is deliberate. The store
    only ever grows, so a multi-snapshot failure could only ever name candidates
    that appeared *after* the lookup — and exposing that requires suspending
    execution between the lookup and the candidate scan, which no barrier placed
    outside ``resolve`` can reach. The single acquisition is the mechanism that
    makes the guarantee true, and it is checkable exactly.
    """
    registry = Registry(("models",))
    registry.add("models", "app", "present", object())
    lock = CountingLock()
    monkeypatch.setattr(registry, "_lock", lock)

    with pytest.raises(UnknownObjectError) as exc:
        registry.resolve("models:app.absent")

    assert lock.acquisitions == 1, (
        f"the failure path observed the store {lock.acquisitions} times; "
        "candidates and the segment verdict must come from one observation"
    )
    assert "present" in str(exc.value), "the failure must still name candidates"

    lock.acquisitions = 0
    registry.resolve("models:app.present")
    assert lock.acquisitions == 1, "the success path must stay a single lookup"


def test_resolution_failures_stay_consistent_under_concurrent_registration():
    """Whatever a failure names, it names from a store state that lacked the target.

    Both sides are bounded on purpose. An unbounded writer makes this quadratic —
    every failing resolve snapshots the store, so a store growing without limit
    turns 400 resolves into an unbounded amount of work. That is a property of
    the failure path at any registry size, not a regression.
    """
    registry = Registry(("models",))
    registry.add("models", "app", "seed", object())
    failures: list[UnknownObjectError] = []
    barrier = threading.Barrier(2)
    ROUNDS = 200

    def register():
        barrier.wait(timeout=5)
        for i in range(ROUNDS):
            registry.add("models", "app", f"late_{i}", object())

    def resolve_missing():
        barrier.wait(timeout=5)
        for _ in range(ROUNDS):
            try:
                registry.resolve("models:app.never_registered")
            except UnknownObjectError as e:
                failures.append(e)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(register), pool.submit(resolve_missing)]
        for f in futures:
            f.result()

    assert len(failures) == ROUNDS, "every resolve of a missing name must fail"
    for failure in failures:
        assert "never_registered" not in failure.candidates, (
            "a failure offered the very identifier its observation lacked"
        )
        # The writer adds late_0..late_n in order and the store only grows, so
        # any single observation holds a contiguous prefix of them. A gap would
        # mean the candidates were assembled from more than one observation.
        late = sorted(
            int(name.removeprefix("late_"))
            for name in failure.candidates
            if name.startswith("late_")
        )
        assert late == list(range(len(late))), (
            f"candidates skip a registration, so they span observations: {late[:12]}"
        )


def test_hook_dispatch_observes_the_registry_once_per_phase(tmp_path, monkeypatch):
    """A lifecycle phase reads the store once, however many modules it dispatches to.

    Counted rather than timed, for the same reason the resolution test above
    counts: the observation is the mechanism, and a stopwatch would assert a
    machine's speed instead of the property. Dispatch used to ask the registry
    per module, which made a phase quadratic in a project's own size — 400
    modules over 50k components spent four seconds walking the store — and made
    each hook's payload a *different* observation from its neighbour's.

    ``on_ready`` fires at the end of discovery and before dispatch begins, so
    zeroing the counter there separates the two phases exactly, without either
    the test or the assertion reaching into how dispatch is implemented.
    """
    apps = {f"app{i}": {"models": MODELS_BODY} for i in range(12)}
    base = ProjectTree(apps=apps).build(tmp_path, "dispatch_observations")
    sys.path.insert(0, str(base))

    fw = Framework(
        KindSpec(
            "models",
            on_startup=lambda objects: None,
            on_shutdown=lambda objects: None,
        )
    )
    lock = CountingLock()
    monkeypatch.setattr(fw.registry, "_lock", lock)
    fw.on_ready(lambda registry: setattr(lock, "acquisitions", 0))

    fw.start(base)
    assert lock.acquisitions == 1, (
        f"startup dispatch observed the store {lock.acquisitions} times for "
        f"{len(apps)} modules; a phase groups once and looks up per module"
    )

    lock.acquisitions = 0
    fw.shutdown()
    assert lock.acquisitions == 1, (
        f"shutdown dispatch observed the store {lock.acquisitions} times for "
        f"{len(apps)} modules; both phases share the one grouping rule"
    )


def test_racing_starts_have_one_winner(tmp_path):
    base = make_project(tmp_path, "raceapp")

    for _ in range(10):
        fw = Framework("models")
        outcomes: list[str] = []

        def attempt(fw=fw, outcomes=outcomes):
            try:
                fw.start(base)
                outcomes.append("won")
            except SpocError as e:
                assert "already started" in str(e)
                outcomes.append("lost")

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt), pool.submit(attempt)]
            for f in futures:
                f.result()

        assert sorted(outcomes) == ["lost", "won"]
        assert [c.identifier for c in fw.registry] == ["models:raceapp.post"]
        fw.shutdown()


def test_shutdown_racing_shutdown_is_harmless(tmp_path):
    base = make_project(tmp_path, "downapp")
    fw = Framework("models").start(base)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fw.shutdown) for _ in range(4)]
        for f in futures:
            assert f.result() is fw

    assert fw.started is False


def test_no_facet_is_observable_without_the_others():
    """A registration is admitted to every view at once (spec: single flat store).

    The index exists so a faceted read need not walk the store; it earns that
    only by being unobservable in a half-written state. Readers run flat out
    against writers and assert the views agree about every record they see.
    """
    registry = Registry(("models", "views"))
    total = 300
    disagreements: list[str] = []
    done = threading.Event()

    def write():
        for i in range(total):
            registry.add("models", f"ns{i % 7}", f"obj{i}", object())
        done.set()

    def read():
        while not done.is_set():
            for record in registry.by_kind("models"):
                if registry.resolve(record.identifier) is not record:
                    disagreements.append(f"{record.identifier}: facet vs store")
                if record.object_name not in registry.object_names(
                    record.kind, record.namespace
                ):
                    disagreements.append(f"{record.identifier}: absent from its facet")
                if not registry.holds(
                    record.kind, record.namespace, record.object_name
                ):
                    disagreements.append(f"{record.identifier}: not held")

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(write), *(pool.submit(read) for _ in range(3))]
        for future in futures:
            future.result()

    assert not disagreements, disagreements[:5]
    assert len(registry) == total
