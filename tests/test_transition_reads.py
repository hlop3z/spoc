"""Reads racing a lifecycle transition (specs: framework-lifecycle, component-resolution).

A transition is a window with an inside and an outside. Code the transition itself
invoked — shutdown hooks, module ``teardown()``, anything they call — resolves
normally. Every other caller is refused with :class:`FrameworkTransitioningError`,
across the whole window: while teardown runs *and* after the registry is swapped.

The point of the error is that it is not an unknown-segment error. A read that lost
a race and a read with a typo used to be indistinguishable, and the tests below pin
both halves of that distinction.

Draining readers is deliberately not the framework's job, so one test here asserts a
*negative*: a shutdown does not wait for a busy reader.
"""

import asyncio
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from spoc import Framework, KindSpec
from spoc.core.exceptions import (
    FrameworkTransitioningError,
    UnknownNamespaceError,
    UnknownObjectError,
)
from spoc.testing import ProjectTree
from tests.conftest import MODELS_BODY, make_project

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")

IDENTIFIER = "models:probeapp.post"

#: A module whose teardown resolves through the framework. No shipped template does
#: this — the shipped starter's shutdown hook iterates the components it is handed —
#: but ``teardown()`` takes no arguments and a hook sees only its own module's
#: components, so this is the only route teardown code has to anything else.
TEARDOWN_READS = """
    from spoc import component

    import probe_state

    @component(kind="models")
    class Post:
        ...

    def teardown():
        probe_state.record_teardown_read()
"""


#: The app reaches the running framework through this module, because ``teardown()``
#: takes no arguments — module-level access is the only shape available to it.
PROBE_STATE = """
framework = None
outcome = None


def record_teardown_read():
    global outcome
    try:
        framework.resolve("models:probeapp.post")
        outcome = "served"
    except BaseException as e:
        outcome = type(e).__name__
"""


@pytest.fixture
def probe_project(tmp_path):
    """A one-app project whose teardown resolves, plus the state module it uses."""
    base = ProjectTree(apps={"probeapp": {"models": TEARDOWN_READS}}).build(
        tmp_path, "proj_probe"
    )
    (base / "probe_state.py").write_text(PROBE_STATE, encoding="utf-8")
    sys.path.insert(0, str(base))
    return base


def _resolve_from_another_thread(fw: Framework, identifier: str = IDENTIFIER):
    """Resolve on a thread that is not the transition's, returning the outcome."""
    outcome: dict[str, object] = {}

    def read():
        try:
            outcome["value"] = fw.resolve(identifier)
            outcome["kind"] = "served"
        except BaseException as e:
            outcome["kind"] = type(e).__name__
            outcome["error"] = e

    thread = threading.Thread(target=read)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive(), "the racing read blocked instead of answering"
    return outcome


# ── The refusal, both windows ────────────────────────────────────────────────


def test_read_during_teardown_is_refused(tmp_path):
    """Window A: teardown is running, the registry is still fully populated."""
    base = make_project(tmp_path, "probeapp")
    seen: dict[str, object] = {}

    def on_shutdown(objects):
        seen.update(_resolve_from_another_thread(fw))

    fw = Framework(KindSpec("models", on_shutdown=on_shutdown)).start(base)
    fw.shutdown()

    assert seen["kind"] == "FrameworkTransitioningError", (
        "a read during teardown was answered from a registry whose components "
        f"were already being torn down: {seen}"
    )


def test_read_after_registry_reset_is_refused_not_reported_as_a_typo(
    tmp_path, monkeypatch
):
    """Window B: the registry has been swapped, so the naive answer is a typo.

    This is the defect stated most sharply — an unknown-namespace error here
    describes an identifier that is perfectly correct. Probing from inside
    ``_reset`` is what pins the window: it is the only instant at which the fresh
    registry is installed and the transition has not yet ended.
    """
    base = make_project(tmp_path, "probeapp")
    fw = Framework("models").start(base)
    seen: dict[str, object] = {}

    original_reset = fw._reset

    def reset_then_probe():
        original_reset()
        seen.update(_resolve_from_another_thread(fw))

    monkeypatch.setattr(fw, "_reset", reset_then_probe)
    fw.shutdown()

    assert seen["kind"] != "UnknownNamespaceError", (
        "a read that lost the race was reported as a typo — the exact confusion "
        "this change exists to remove"
    )
    assert seen["kind"] == "FrameworkTransitioningError", seen


def test_the_error_names_the_identifier_and_the_transition(tmp_path):
    base = make_project(tmp_path, "probeapp")
    seen: dict[str, object] = {}

    def on_shutdown(objects):
        seen.update(_resolve_from_another_thread(fw))

    fw = Framework(KindSpec("models", on_shutdown=on_shutdown)).start(base)
    fw.shutdown()

    error = seen["error"]
    assert isinstance(error, FrameworkTransitioningError)
    assert error.identifier == IDENTIFIER
    assert "shutdown" in error.transition
    assert IDENTIFIER in str(error)


# ── What must not change ─────────────────────────────────────────────────────


def test_a_genuine_typo_is_still_a_segment_failure(tmp_path):
    base = make_project(tmp_path, "probeapp")
    fw = Framework("models").start(base)

    with pytest.raises(UnknownNamespaceError) as exc:
        fw.resolve("models:blogg.post")
    assert "probeapp" in str(exc.value), "the failure must still name candidates"

    with pytest.raises(UnknownObjectError):
        fw.resolve("models:probeapp.pots")

    fw.shutdown()


def test_a_settled_framework_resolves_normally(tmp_path):
    base = make_project(tmp_path, "probeapp")
    fw = Framework("models").start(base)

    assert fw.resolve(IDENTIFIER).identifier == IDENTIFIER
    assert _resolve_from_another_thread(fw)["kind"] == "served", (
        "a read on a settled framework needs no coordination"
    )

    fw.shutdown()


def test_a_never_started_framework_still_answers_unknown_segment():
    """The refusal covers transitions, not the inert state.

    An empty registry is deterministic misuse, not a race, and stays out of scope.
    """
    fw = Framework("models")
    with pytest.raises(UnknownNamespaceError):
        fw.resolve(IDENTIFIER)


# ── The exemption ────────────────────────────────────────────────────────────


def test_teardown_resolves_during_its_own_shutdown(probe_project):
    """The pattern the starter template teaches must keep working."""
    import probe_state

    fw = Framework("models").start(probe_project)
    probe_state.framework = fw
    fw.shutdown()

    assert probe_state.outcome == "served", (
        "a module teardown could not reach the components it exists to tear "
        f"down: {probe_state.outcome}"
    )


def test_the_exemption_does_not_leak_to_a_concurrent_caller(probe_project):
    """Teardown's read is served in the same instant an outside read is refused."""
    import probe_state

    outside: dict[str, object] = {}

    def on_shutdown(objects):
        outside.update(_resolve_from_another_thread(fw))

    fw = Framework(KindSpec("models", on_shutdown=on_shutdown)).start(probe_project)
    probe_state.framework = fw
    fw.shutdown()

    assert probe_state.outcome == "served", "the transition's own read was refused"
    assert outside["kind"] == "FrameworkTransitioningError", (
        "the exemption was visible to a caller outside the transition"
    )


def test_the_exemption_ends_with_the_transition(tmp_path):
    """The marker is reset, so the thread that ran a shutdown is not exempt after."""
    base = make_project(tmp_path, "probeapp")
    fw = Framework("models").start(base)
    fw.shutdown()

    assert fw._transitions._label is None
    assert not fw._transitions.inside, (
        "the transition marker survived the transition; every later read on this "
        "thread would be exempt"
    )
    with pytest.raises(UnknownNamespaceError):
        fw.resolve(IDENTIFIER)  # inert, so a segment failure — not a served read


def test_two_frameworks_do_not_cross_exempt(tmp_path):
    """A transition on one framework says nothing about reads on another."""
    base_a = make_project(tmp_path, "probeapp")
    other = Framework("models")
    seen: dict[str, object] = {}

    def on_shutdown(objects):
        # Inside A's transition, but B is settled: B must answer for itself.
        try:
            other.resolve(IDENTIFIER)
            seen["b"] = "served"
        except BaseException as e:
            seen["b"] = type(e).__name__

    fw = Framework(KindSpec("models", on_shutdown=on_shutdown)).start(base_a)
    fw.shutdown()

    assert seen["b"] == "UnknownNamespaceError", (
        "framework B answered from framework A's lifecycle state"
    )


# ── Start is a transition too ────────────────────────────────────────────────


def test_start_refuses_an_outside_read_while_in_boot_code_resolves(tmp_path):
    """Discovery populates incrementally, so a racing read sees a partial registry."""
    base = make_project(tmp_path, "probeapp")
    seen: dict[str, object] = {}
    inside: dict[str, object] = {}

    def on_ready(registry):
        seen.update(_resolve_from_another_thread(fw))
        try:
            inside["ready"] = fw.resolve(IDENTIFIER).identifier
        except BaseException as e:
            inside["ready"] = type(e).__name__

    fw = Framework("models")
    fw.on_ready(on_ready)
    fw.start(base)

    assert seen["kind"] == "FrameworkTransitioningError", (
        f"a read racing a boot was served a half-built registry: {seen}"
    )
    assert inside["ready"] == IDENTIFIER, (
        "a ready callback is inside the transition and must resolve"
    )
    fw.shutdown()


def test_read_racing_a_failed_boot_rollback_is_refused(tmp_path, monkeypatch):
    """Rollback swaps the registry exactly as shutdown does, so Window B lives here too."""
    # MODELS_BODY is written indented and dedented on build, so the appended
    # lines have to match its indentation or the module will not parse.
    failing = (
        MODELS_BODY + "\n    def initialize():\n        raise RuntimeError('boom')\n"
    )
    base = make_project(tmp_path, "probeapp", models_body=failing)
    seen: dict[str, object] = {}

    fw = Framework("models")
    original_reset = fw._reset

    def reset_then_probe():
        original_reset()
        if "kind" not in seen:
            seen.update(_resolve_from_another_thread(fw))

    monkeypatch.setattr(fw, "_reset", reset_then_probe)

    with pytest.raises(RuntimeError, match="boom"):
        fw.start(base)

    assert seen["kind"] == "FrameworkTransitioningError", (
        f"a read racing a failed boot's rollback was answered as a typo: {seen}"
    )


# ── Both lifecycle paths classify identically ────────────────────────────────


def test_async_shutdown_classifies_inside_and_outside_identically(probe_project):
    """The async path is where thread identity fails and the context variable earns itself.

    Every task here runs on one thread, so a thread-based discriminator would mistake
    the racing task for teardown code and exempt it. The probes all fire from inside
    an async shutdown hook, which is the only point at which the transition is
    genuinely in flight.
    """
    import probe_state

    results: dict[str, object] = {}
    gate = asyncio.Event()

    async def predates_the_transition():
        """Created before the shutdown, so its context copy has no marker."""
        await gate.wait()
        try:
            state["fw"].resolve(IDENTIFIER)
            results["preexisting_task"] = "served"
        except BaseException as e:
            results["preexisting_task"] = type(e).__name__

    async def on_shutdown(objects):
        # Another thread: a fresh context, so outside the transition.
        results["other_thread"] = _resolve_from_another_thread(state["fw"])["kind"]
        # A task that predates the transition: same thread, older context.
        gate.set()
        await asyncio.sleep(0)
        # This hook itself, awaited inline by the loader: inside.
        try:
            state["fw"].resolve(IDENTIFIER)
            results["hook_inline"] = "served"
        except BaseException as e:
            results["hook_inline"] = type(e).__name__

    state: dict[str, Framework] = {}

    async def scenario():
        fw = Framework(KindSpec("models", on_shutdown=on_shutdown))
        state["fw"] = fw
        await fw.astart(probe_project)
        probe_state.framework = fw
        racing = asyncio.create_task(predates_the_transition())
        await asyncio.sleep(0)  # let it start and park, before any transition
        await fw.ashutdown()
        await racing

    asyncio.run(scenario())

    assert results["hook_inline"] == "served", (
        "an async shutdown hook was refused its own read; the exemption does not "
        "reach the asynchronous path"
    )
    assert probe_state.outcome == "served", "an async module teardown could not resolve"
    assert results["other_thread"] == "FrameworkTransitioningError", (
        "a racing thread was served during an async shutdown"
    )
    assert results["preexisting_task"] == "FrameworkTransitioningError", (
        "a task that predates the transition was exempted — this is exactly what "
        "a thread-identity discriminator would get wrong, since it shares a thread "
        "with the shutdown"
    )


def test_work_spawned_by_teardown_inherits_the_exemption(tmp_path):
    """Stated property, not a leak: work spawned by teardown is teardown.

    ``create_task`` copies the spawner's context, so only code already inside the
    transition can propagate the marker. Pinned as a test because it looks like a
    leak and is not — and because silently losing it would break a hook that does
    its teardown concurrently.
    """
    base = make_project(tmp_path, "probeapp")
    seen: dict[str, object] = {}

    async def on_shutdown(objects):
        async def spawned():
            try:
                state["fw"].resolve(IDENTIFIER)
                seen["spawned"] = "served"
            except BaseException as e:
                seen["spawned"] = type(e).__name__

        # Awaited inside the hook, so it runs while the transition is genuinely
        # in flight — spawning it and awaiting it afterwards would prove nothing,
        # because by then there is no transition to be exempt from.
        await asyncio.create_task(spawned())

    state: dict[str, Framework] = {}

    async def scenario():
        fw = Framework(KindSpec("models", on_shutdown=on_shutdown))
        state["fw"] = fw
        await fw.astart(base)
        await fw.ashutdown()

    asyncio.run(scenario())

    assert seen["spawned"] == "served", (
        "a task spawned by a shutdown hook did not inherit the exemption; "
        f"contextvars are copied at task creation, so it should have: {seen}"
    )


# ── The negative: no draining ────────────────────────────────────────────────


def test_shutdown_does_not_block_on_a_busy_reader(tmp_path):
    """Draining is the host's job. A shutdown must not wait for a reader to stop."""
    base = make_project(tmp_path, "probeapp")
    fw = Framework("models").start(base)

    stop = threading.Event()
    refusals = []

    def hammer():
        while not stop.is_set():
            try:
                fw.resolve(IDENTIFIER)
            except FrameworkTransitioningError:
                refusals.append(1)
            except UnknownNamespaceError:
                pass  # settled-but-inert, after shutdown completes

    with ThreadPoolExecutor(max_workers=1) as pool:
        reader = pool.submit(hammer)
        try:
            fw.shutdown()  # must return without waiting for `hammer`
        finally:
            stop.set()
            reader.result(timeout=5)

    assert fw.started is False


# ── The typed accessors refuse on the same terms ─────────────────────────────


def test_typed_accessors_refuse_on_the_same_terms(tmp_path):
    base = make_project(tmp_path, "probeapp")
    outcomes: dict[str, str] = {}

    def on_shutdown(objects):
        for name, call in (
            ("resolve", lambda: fw.resolve(IDENTIFIER)),
            ("resolve_type", lambda: fw.resolve_type(IDENTIFIER, object)),
            ("resolve_object", lambda: fw.resolve_object(IDENTIFIER, object)),
        ):
            result: dict[str, str] = {}

            def read(call=call, result=result):
                try:
                    call()
                    result["kind"] = "served"
                except BaseException as e:
                    result["kind"] = type(e).__name__

            thread = threading.Thread(target=read)
            thread.start()
            thread.join(timeout=5)
            outcomes[name] = result["kind"]

    fw = Framework(KindSpec("models", on_shutdown=on_shutdown)).start(base)
    fw.shutdown()

    assert outcomes == {
        "resolve": "FrameworkTransitioningError",
        "resolve_type": "FrameworkTransitioningError",
        "resolve_object": "FrameworkTransitioningError",
    }, f"the read accessors disagree about the refusal: {outcomes}"
