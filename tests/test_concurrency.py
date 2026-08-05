"""
The concurrency contract (specs: component-registry, framework-lifecycle).

Registration is serialized and loses nothing; duplicate and divergence
guarantees hold under any interleaving; lifecycle transitions are mutually
exclusive with exactly one winner.
"""

from concurrent.futures import ThreadPoolExecutor

import pytest

from spoc import Framework
from spoc.core.exceptions import DuplicateComponentError, SpocError
from spoc.core.registry import Registry
from tests.conftest import make_project

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
    """Two objects racing the same identifier: one record, one loud loser."""
    for _ in range(20):  # a race needs repetitions to be a test at all
        registry = Registry(("models",))
        outcomes: list[str] = []

        def attempt(registry=registry, outcomes=outcomes):
            try:
                registry.add("models", "app", "contested", object())
                outcomes.append("won")
            except DuplicateComponentError:
                outcomes.append("lost")

        with ThreadPoolExecutor(max_workers=2) as pool:
            pool.submit(attempt).result()
            pool.submit(attempt).result()

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
