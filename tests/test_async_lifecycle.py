"""
The asynchronous lifecycle path (spec: framework-lifecycle).

astart/ashutdown await coroutine hooks and module initialize/teardown; the
synchronous path refuses coroutines loudly and rolls back rather than
half-running them.
"""

import asyncio

import pytest

from spoc import Framework, KindSpec
from spoc.core.exceptions import SpocError
from tests.conftest import MODELS_BODY, make_project

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")


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
