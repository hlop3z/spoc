"""
Reaching the inert state is unconditional (spec: framework-lifecycle).

Every guarantee here is about what the framework owes when app-authored
lifecycle code raises. Propagating the failure and reaching the inert state are
not traded off against each other: a transition out of started resets kernel
state whether or not the code it invoked succeeded, and whether or not the
rollback of a failed boot succeeded either.

The defect these pin: a raising ``teardown()`` used to skip both the reset and
the started flag, leaving the framework reporting itself started, refusing
``start()`` as "already started", and re-raising the same teardown forever
because the loader never cleared its own flag. The only escape was a new
``Framework``.
"""

import asyncio
import logging

import pytest

from spoc import Framework, KindSpec
from spoc.core.exceptions import CoroutineLifecycleError
from spoc.testing import ProjectTree
from tests.conftest import MODELS_BODY, make_project

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")

RAISING_TEARDOWN = """
    from spoc import component

    @component(kind="models")
    class Post:
        ...

    def teardown():
        raise RuntimeError("teardown boom")
"""

ASYNC_RAISING_TEARDOWN = """
    from spoc import component

    @component(kind="models")
    class Post:
        ...

    async def teardown():
        raise RuntimeError("async teardown boom")
"""


def assert_inert(fw: Framework) -> None:
    """Every piece of kernel-owned state is back to its pre-start value."""
    assert fw.started is False, "framework still reports itself started"
    assert len(fw.registry) == 0, "registry was not reset"
    assert fw.config is None, "configuration was not reset"
    assert len(fw.loader) == 0, "module bookkeeping was not reset"


def test_failing_teardown_leaves_the_framework_restartable(tmp_path):
    base = make_project(tmp_path, "wedgeteardown", models_body=RAISING_TEARDOWN)
    fw = Framework("models").start(base)

    with pytest.raises(RuntimeError, match="teardown boom"):
        fw.shutdown()

    assert_inert(fw)
    fw.start(base)
    assert fw.started is True
    assert [c.identifier for c in fw.registry] == ["models:wedgeteardown.post"]


def test_failing_shutdown_hook_leaves_the_framework_restartable(tmp_path):
    base = make_project(tmp_path, "wedgehook")

    def on_shutdown(components):
        raise RuntimeError("shutdown hook boom")

    fw = Framework(KindSpec("models", on_shutdown=on_shutdown)).start(base)

    with pytest.raises(RuntimeError, match="shutdown hook boom"):
        fw.shutdown()

    assert_inert(fw)
    fw.start(base)
    assert fw.started is True


def test_second_shutdown_after_a_failed_one_is_a_no_op(tmp_path):
    """The teardown must not be re-offered forever by a loader that was never reset."""
    base = make_project(tmp_path, "repeatshutdown", models_body=RAISING_TEARDOWN)
    fw = Framework("models").start(base)

    with pytest.raises(RuntimeError, match="teardown boom"):
        fw.shutdown()

    assert fw.shutdown() is fw, "a second shutdown re-ran the failing teardown"
    assert_inert(fw)


class Interrupt(BaseException):
    """A BaseException, as KeyboardInterrupt is, without disturbing the test runner."""


def test_failure_during_rollback_does_not_strand_kernel_state(tmp_path):
    """The boot's cause reaches the caller; the rollback's own failure does not mask it.

    The rollback failure must be a ``BaseException`` to pin this: rollback already
    guards against ``Exception``, so a ``RuntimeError`` here would test nothing.
    """
    base = make_project(
        tmp_path,
        "rollbackfails",
        models_body="""
            from spoc import component

            @component(kind="models")
            class Post:
                ...

            def initialize():
                raise RuntimeError("the cause")
        """,
    )

    def on_shutdown(components):
        raise Interrupt("raised while cleaning up")

    fw = Framework(KindSpec("models", on_shutdown=on_shutdown))

    with pytest.raises(RuntimeError, match="the cause"):
        fw.start(base)

    assert_inert(fw)


def test_the_package_logger_has_a_handler_so_last_resort_cannot_fire():
    """The mechanism, asserted directly — a stderr test here would prove nothing.

    ``lastResort`` writes WARNING and above to stderr only when a record finds
    no handler. pytest's logging plugin attaches one to the root logger for the
    duration of every test, so ``lastResort`` cannot fire inside this suite
    whether or not the package registers anything. Asserting on captured stderr
    would therefore pass with or without the ``NullHandler``. What is checkable
    is the guard itself.
    """
    handlers = logging.getLogger("spoc").handlers
    assert handlers, "the spoc logger has no handler; lastResort would reach stderr"
    assert any(isinstance(h, logging.NullHandler) for h in handlers)


def test_a_rollback_failure_is_recorded_for_a_consumer_who_wants_it(tmp_path, caplog):
    """The NullHandler silences nothing: an attached handler still sees the record."""
    base = make_project(
        tmp_path,
        "rollbacklog",
        models_body="""
            from spoc import component

            @component(kind="models")
            class Post:
                ...

            def initialize():
                raise RuntimeError("the cause")
        """,
    )

    def on_shutdown(components):
        raise Interrupt("raised while cleaning up")

    fw = Framework(KindSpec("models", on_shutdown=on_shutdown))

    with (
        caplog.at_level(logging.ERROR, logger="spoc"),
        pytest.raises(RuntimeError, match="the cause"),
    ):
        fw.start(base)

    records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(records) == 1, "the rollback failure was not recorded exactly once"
    assert records[0].name == "spoc.framework", (
        "the record must carry a module-path logger name, not a hardcoded one"
    )
    assert records[0].exc_info is not None, (
        "the rollback failure was flattened into a message instead of carrying "
        "its exception, which is what an OpenTelemetry bridge would consume"
    )
    assert "inert state" in records[0].getMessage()


def test_async_failing_teardown_leaves_the_framework_restartable(tmp_path):
    base = make_project(tmp_path, "asyncwedge", models_body=ASYNC_RAISING_TEARDOWN)
    fw = Framework("models")

    async def run():
        await fw.astart(base)
        with pytest.raises(RuntimeError, match="async teardown boom"):
            await fw.ashutdown()
        assert_inert(fw)
        await fw.astart(base)
        assert fw.started is True

    asyncio.run(run())


def test_sync_refusal_precedes_every_lifecycle_side_effect(tmp_path, monkeypatch):
    """A coroutine in the last app refuses before the first app's initialize runs.

    The first app records having run by creating a file, so the side effect is
    observable from outside the process's import state.
    """
    ran: list[str] = []
    sentinel = tmp_path / "first_app_initialized"
    base = ProjectTree(
        apps={
            "first": {
                "models": MODELS_BODY
                + f"""
    def initialize():
        from pathlib import Path

        Path({str(sentinel)!r}).touch()
"""
            },
            "second": {
                "models": MODELS_BODY
                + """
    async def initialize():
        ...
"""
            },
        },
    ).build(tmp_path, "proj_preflight")
    monkeypatch.syspath_prepend(str(base))

    fw = Framework(KindSpec("models", on_startup=lambda c: ran.append("up")))

    with pytest.raises(CoroutineLifecycleError) as exc:
        fw.start(base)

    assert "coroutine" in str(exc.value)
    assert exc.value.phase == "startup"
    assert not sentinel.exists(), (
        "an earlier app's initialize ran before the coroutine refusal"
    )
    assert ran == [], "a startup hook fired before the coroutine refusal"
    assert_inert(fw)
