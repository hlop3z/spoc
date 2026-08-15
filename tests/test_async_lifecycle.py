"""
The asynchronous lifecycle path (spec: framework-lifecycle).

astart/ashutdown await coroutine hooks and module initialize/teardown; the
synchronous path refuses coroutines loudly and rolls back rather than
half-running them.
"""

import asyncio
import threading

import pytest

from spoc import Framework, KindSpec
from spoc.core.exceptions import SpocError
from tests.conftest import MODELS_BODY, make_project

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")

#: Long enough that a loaded machine never trips it, short enough that a stalled
#: run reports instead of occupying CI until something outside kills it.
_WALL_CLOCK = 10


def run_bounded(scenario, seconds: int = _WALL_CLOCK) -> None:
    """Run an async scenario under a wall-clock bound, on a thread of its own.

    Every scenario that races a caller against an in-flight transition can only
    fail two ways: the caller is refused, or it waits. If it waits, it waits on a
    lock held by work scheduled on the same event loop, so nothing inside that
    loop can time it out — the loop is the thing that stopped. Bounding it from
    outside is what turns that from a hang into an assertion.

    The thread is a daemon so a stalled scenario cannot keep the interpreter
    alive after the failure is reported.
    """
    finished = threading.Event()
    failure: dict[str, BaseException] = {}

    def run():
        try:
            asyncio.run(scenario())
        except BaseException as e:  # re-raised below, on the calling thread
            failure["error"] = e
        finally:
            finished.set()

    threading.Thread(target=run, daemon=True).start()
    assert finished.wait(timeout=seconds), (
        f"the scenario did not settle within {seconds}s — the asynchronous path "
        "waited for an in-flight transition instead of refusing it, parking the "
        "event loop on a lock only that loop could release"
    )
    if "error" in failure:
        raise failure["error"]


def test_astart_awaits_coroutine_hooks_in_order(tmp_path):
    base = make_project(tmp_path, "ahooks")
    events: list[str] = []

    async def up(objects):
        await asyncio.sleep(0)
        events.append(f"up:{len(objects)}")

    async def down(objects):
        await asyncio.sleep(0)
        events.append("down")

    fw = Framework(KindSpec("models", on_startup=up, on_shutdown=down))

    async def run():
        await fw.astart(base)
        assert fw.started is True
        await fw.ashutdown()

    asyncio.run(run())
    assert events == ["up:1", "down"]
    assert fw.started is False


def test_astart_awaits_coroutine_module_initialize(tmp_path):
    base = make_project(
        tmp_path,
        "amod",
        MODELS_BODY
        + """
    events = []

    async def initialize():
        events.append("init")

    async def teardown():
        events.append("teardown")
    """,
    )
    fw = Framework("models")

    async def run():
        await fw.astart(base)
        await fw.ashutdown()

    asyncio.run(run())
    import amod.models

    assert amod.models.events == ["init", "teardown"]


def test_astart_runs_plain_hooks_too(tmp_path):
    """The async path is a superset: plain hooks run exactly as they would."""
    base = make_project(tmp_path, "aplain")
    seen: list[int] = []
    fw = Framework(KindSpec("models", on_startup=lambda objs: seen.append(len(objs))))

    asyncio.run(fw.astart(base))
    assert seen == [1]
    asyncio.run(fw.ashutdown())


def test_sync_start_refuses_coroutine_hook_and_rolls_back(tmp_path):
    base = make_project(tmp_path, "srefuse")

    async def up(objects): ...

    fw = Framework(KindSpec("models", on_startup=up))
    with pytest.raises(SpocError, match="astart"):
        fw.start(base)

    assert fw.started is False
    assert len(fw.registry) == 0  # rolled back to inert


def test_sync_start_refuses_coroutine_module_initialize(tmp_path):
    base = make_project(
        tmp_path,
        "srefusemod",
        MODELS_BODY + "\n    async def initialize():\n        ...\n",
    )
    fw = Framework("models")
    with pytest.raises(SpocError, match=r"srefusemod\.models\.initialize"):
        fw.start(base)
    assert fw.started is False


def test_async_teardown_runs_in_reverse_dependency_order(tmp_path):
    base = make_project(
        tmp_path,
        "aorder",
        MODELS_BODY
        + """
    async def teardown():
        import atrace
        atrace.events.append("models")
    """,
        extra_modules={
            "views": (
                "async def teardown():\n"
                "    import atrace\n"
                '    atrace.events.append("views")\n'
            )
        },
    )
    (base / "atrace.py").write_text("events = []\n")
    import atrace

    fw = Framework("models", KindSpec("views", depends_on=("models",)))

    async def run():
        await fw.astart(base)
        await fw.ashutdown()

    asyncio.run(run())
    assert atrace.events == ["views", "models"]


def test_failed_astart_rolls_back_and_stays_retryable(tmp_path):
    base = make_project(
        tmp_path,
        "aroll",
        MODELS_BODY
        + """
    async def initialize():
        raise RuntimeError("async boom")
    """,
    )
    fw = Framework("models")
    # The app's own error surfaces unwrapped — the doctrine holds on the
    # async path too — and the failed boot still rolls back to inert.
    with pytest.raises(RuntimeError, match="async boom"):
        asyncio.run(fw.astart(base))
    assert fw.started is False
    assert len(fw.registry) == 0


def test_astart_on_started_framework_raises(tmp_path):
    base = make_project(tmp_path, "atwice")
    fw = Framework("models").start(base)
    with pytest.raises(SpocError, match="already started"):
        asyncio.run(fw.astart(base))
    fw.shutdown()


def test_ashutdown_without_start_is_noop():
    fw = Framework("models")
    assert asyncio.run(fw.ashutdown()) is fw
    assert fw.started is False


# ── Reentrant vs concurrent, told apart on one thread ────────────────────────


def test_concurrent_atransition_is_not_reported_as_reentrant(tmp_path):
    """A racing task shares the loop thread but is not inside the transition.

    The two conditions have opposite remedies — a concurrent caller may retry once
    the transition settles, a reentrant one never can — so answering one with the
    other's error argues the caller out of the fix that would work.
    """
    base = make_project(tmp_path, "aconcurrent")
    gate = asyncio.Event()
    seen: dict[str, str] = {}
    state: dict[str, Framework] = {}

    async def predates_the_transition():
        """Created before the shutdown, so its context copy carries no marker."""
        await gate.wait()
        try:
            await state["fw"].astart(base)
            seen["racing"] = "served"
        except SpocError as e:
            seen["racing"] = str(e)

    async def on_shutdown(objects):
        gate.set()
        await asyncio.sleep(0)  # let the racing task run while shutdown is in flight

    async def scenario():
        fw = Framework(KindSpec("models", on_shutdown=on_shutdown))
        state["fw"] = fw
        await fw.astart(base)
        racing = asyncio.create_task(predates_the_transition())
        await asyncio.sleep(0)  # let it start and park, before any transition
        await fw.ashutdown()
        await racing

    # Bounded: if the racing astart ever waits for the lock instead of refusing
    # it, this scenario stops rather than fails, and a stopped test reports
    # nothing.
    run_bounded(scenario)

    assert "already in progress" in seen["racing"], (
        f"a task racing an in-flight transition got the wrong diagnosis: {seen['racing']!r}"
    )
    assert "inside a lifecycle transition" not in seen["racing"], (
        "a concurrent caller was told it reentered — it shares the event loop thread "
        "with the transition, which is what a thread-identity check mistakes for reentry"
    )


def test_atransition_spawned_by_a_hook_is_reentrant(tmp_path):
    """Work a transition spawns is part of it, so its inner transition is reentry.

    ``create_task`` copies the spawner's context, so the marker reaches this task and
    not the one above — which is the whole distinction the fold relies on.
    """
    base = make_project(tmp_path, "aspawnedreentry")
    seen: dict[str, str] = {}
    state: dict[str, Framework] = {}

    async def on_shutdown(objects):
        async def spawned():
            try:
                await state["fw"].ashutdown()
                seen["spawned"] = "served"
            except SpocError as e:
                seen["spawned"] = str(e)

        # Awaited inside the hook, so it runs while the transition is genuinely
        # in flight rather than after it has settled.
        await asyncio.create_task(spawned())

    async def scenario():
        fw = Framework(KindSpec("models", on_shutdown=on_shutdown))
        state["fw"] = fw
        await fw.astart(base)
        await fw.ashutdown()

    asyncio.run(scenario())

    assert "inside a lifecycle transition" in seen["spawned"], (
        f"a task spawned by a shutdown hook was not treated as inside it: {seen['spawned']!r}"
    )


def test_a_busy_framework_is_refused_without_parking_the_event_loop(tmp_path):
    """Refusing a busy framework is not the same promise as not deadlocking.

    A blocking acquire does not deadlock — it does eventually get the lock — so
    it satisfies every other requirement here while stalling every unrelated task
    the caller is running. On this path it is worse than a stall: the transition
    holding the lock is running on this same thread, so blocking for it can never
    let it finish.

    The scenario runs under a wall-clock bound because that is the failure this
    pins: a blocking implementation would hang here rather than assert.
    """
    base = make_project(tmp_path, "abusy")
    seen: dict[str, str] = {}
    state: dict[str, Framework] = {}
    ticks = 0

    async def ticker(release):
        """Unrelated scheduled work: it must keep advancing while the refusal happens."""
        nonlocal ticks
        while not release.is_set():
            ticks += 1
            await asyncio.sleep(0)

    async def racing(release):
        try:
            await state["fw"].astart(base)
            seen["racing"] = "served"
        except SpocError as e:
            seen["racing"] = str(e)
        release.set()

    async def scenario():
        release = asyncio.Event()

        async def on_shutdown(objects):
            # Holds the transition open until the racing caller has been answered,
            # so the refusal is decided while the lock is genuinely held.
            await release.wait()

        fw = Framework(KindSpec("models", on_shutdown=on_shutdown))
        state["fw"] = fw
        await fw.astart(base)
        # Created before the transition, so neither copies its marker: both are
        # outside it, which is what makes one racing rather than reentrant.
        work = asyncio.gather(ticker(release), racing(release))
        await fw.ashutdown()
        await work

    run_bounded(scenario)

    assert "already in progress" in seen["racing"], (
        f"a caller refused for a busy framework got the wrong diagnosis: {seen['racing']!r}"
    )
    assert ticks > 0, (
        "unrelated scheduled work never ran while the transition was in flight, "
        "so the refusal cost the loop its progress even though it did return"
    )
