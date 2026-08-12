"""
The load-order contract (spec: framework-lifecycle, framework-declaration).

These tests pin the order the kernel produces *today*, before the ordering rule moves
from `graphlib`'s level batching to an owned `(kind_depth, app_index)` key. They are
written to pass unchanged on both sides of that move: if any of them changes, the move
changed behaviour and is wrong.

Three orders exist in a boot and only two of them are the contract:

* **import** — `Loader.register` imports each module as it registers it, app by app, so
  `blog.views` is imported before `shop.models`. Nothing depends on this: decorators only
  mark, and `discover()` populates the registry later.
* **discovery** — `Framework.start` walks `loader.ordered()` to register components.
* **initialize / hooks** — `Loader.initialize` walks the same order.

The barrier is a claim about the last two. `test_import_order_is_app_major` pins the first
one precisely because it is *not* the barrier, so a future reader does not mistake it for a
violation.
"""

import sys
from importlib import import_module
from itertools import pairwise
from pathlib import Path

import pytest

from spoc import Framework, KindSpec
from spoc.core.exceptions import CircularDependencyError
from spoc.testing import ProjectTree

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")

KIND_CHAIN = ("models", "views", "urls")

MODULE_SOURCE = """
from spoc import component

import {trace}

{trace}.events.append("import:{app}.{kind}")


@component(kind="{kind}")
class Thing:
    where = "{app}.{kind}"


def initialize():
    {trace}.events.append("init:{app}.{kind}")


def teardown():
    {trace}.events.append("down:{app}.{kind}")
"""


def build(
    tmp_path: Path,
    trace: str,
    apps: tuple[str, ...] = ("blog", "shop"),
    kinds: tuple[str, ...] = KIND_CHAIN,
) -> Path:
    """A multi-app, multi-kind project whose every module reports what it did.

    `apps` is written to the config verbatim rather than sorted, so the declaration
    order under test is the one the project states.
    """
    base = ProjectTree(
        apps={
            app: {
                kind: MODULE_SOURCE.format(trace=trace, app=app, kind=kind)
                for kind in kinds
            }
            for app in apps
        },
        config={"apps": {"development": list(apps)}},
    ).build(tmp_path, f"proj_{trace}")
    (base / f"{trace}.py").write_text("events = []\n", encoding="utf-8")
    sys.path.insert(0, str(base))
    return base


def framework(trace, kinds: tuple[str, ...] = KIND_CHAIN) -> Framework:
    """A framework whose kinds form a dependency chain and whose hooks report."""
    specs = [
        KindSpec(
            kind,
            depends_on=(kinds[index - 1],) if index else (),
            on_startup=lambda objects: trace.events.append(f"hook:{objects[0].where}"),
            on_shutdown=lambda objects: trace.events.append(
                f"hookdown:{objects[0].where}"
            ),
        )
        for index, kind in enumerate(kinds)
    ]
    return Framework(*specs)


def phase_of(module: str) -> str:
    return module.split(".")[1]


def only(events: list[str], prefix: str) -> list[str]:
    return [e.split(":", 1)[1] for e in events if e.startswith(f"{prefix}:")]


def assert_phases_do_not_interleave(order: list[str], kinds=KIND_CHAIN) -> None:
    """Every module of a kind precedes every module of the kind that depends on it."""
    positions = {
        kind: [i for i, module in enumerate(order) if phase_of(module) == kind]
        for kind in kinds
    }
    for earlier, later in pairwise(kinds):
        assert positions[earlier] and positions[later], (earlier, later, order)
        assert max(positions[earlier]) < min(positions[later]), order


# ── 2.1 The cross-app phase barrier ───────────────────────────────────────


def test_cross_app_phase_barrier(tmp_path):
    """No app's dependent module initializes before any app's depended-on module."""
    base = build(tmp_path, "tr_barrier")
    trace = import_module("tr_barrier")
    fw = framework(trace)
    fw.start(base)
    try:
        order = only(trace.events, "init")
        assert order == [
            "blog.models",
            "shop.models",
            "blog.views",
            "shop.views",
            "blog.urls",
            "shop.urls",
        ]
        assert_phases_do_not_interleave(order)
    finally:
        fw.shutdown()


def test_discovery_walks_the_same_order(tmp_path):
    """Registry population is the other consumer of the order, and shares it."""
    base = build(tmp_path, "tr_discovery")
    trace = import_module("tr_discovery")
    fw = framework(trace)
    fw.start(base)
    try:
        loaded = [entry.name for entry in fw.loader.ordered()]
        assert loaded == only(trace.events, "init")
        assert_phases_do_not_interleave(loaded)
    finally:
        fw.shutdown()


def test_import_order_is_app_major_and_is_not_the_contract(tmp_path):
    """Registration imports app by app; only the ordered walk carries the guarantee.

    Pinned so the distinction stays visible: an app's `views` module is *imported*
    before another app's `models` module, and that is fine, because importing only
    marks. If this ever coincides with the initialize order, the pin below still
    holds and this test is the one to re-read.
    """
    base = build(tmp_path, "tr_import")
    trace = import_module("tr_import")
    fw = framework(trace)
    fw.start(base)
    try:
        assert only(trace.events, "import") == [
            "blog.models",
            "blog.views",
            "blog.urls",
            "shop.models",
            "shop.views",
            "shop.urls",
        ]
    finally:
        fw.shutdown()


# ── 2.2 The declaration-order tiebreak ────────────────────────────────────


@pytest.mark.parametrize("apps", [("blog", "shop"), ("shop", "blog")])
def test_app_list_order_breaks_ties_within_a_phase(tmp_path, apps):
    """The `[spoc.apps]` order decides within a kind phase, and only within one."""
    trace_name = f"tr_tie_{apps[0]}"
    base = build(tmp_path, trace_name, apps=apps)
    trace = import_module(trace_name)
    fw = framework(trace)
    fw.start(base)
    try:
        order = only(trace.events, "init")
        assert order == [f"{app}.{kind}" for kind in KIND_CHAIN for app in apps]
        assert_phases_do_not_interleave(order)
        for kind in KIND_CHAIN:
            in_phase = [m for m in order if phase_of(m) == kind]
            assert [m.split(".")[0] for m in in_phase] == list(apps)
    finally:
        fw.shutdown()


@pytest.mark.parametrize("apps", [("blog", "shop"), ("shop", "blog")])
def test_absent_optional_module_does_not_shift_the_others(tmp_path, apps):
    """An app that omits an optional kind leaves every other position untouched.

    This was a defect until kind rank came from the declaration. An absent optional
    module never reaches the module graph through its own registration, but the
    dependent's registration put the name back as a node with no predecessors, which
    landed it at level 0 — so with `shop` omitting `views`, `shop.urls` initialized
    a whole phase early, ahead of `blog.views`. A rank read from the declaration
    cannot be moved by a module that does not exist.
    """
    trace_name = f"tr_optional_{apps[0]}"
    base = ProjectTree(
        apps={
            "blog": {
                kind: MODULE_SOURCE.format(trace=trace_name, app="blog", kind=kind)
                for kind in KIND_CHAIN
            },
            "shop": {
                kind: MODULE_SOURCE.format(trace=trace_name, app="shop", kind=kind)
                for kind in ("models", "urls")
            },
        },
        config={"apps": {"development": list(apps)}},
    ).build(tmp_path, f"proj_optional_{apps[0]}")
    (base / f"{trace_name}.py").write_text("events = []\n", encoding="utf-8")
    sys.path.insert(0, str(base))
    trace = import_module(trace_name)

    fw = Framework(
        KindSpec("models"),
        KindSpec("views", depends_on=("models",), required=False),
        KindSpec("urls", depends_on=("views",)),
    )
    fw.start(base)
    try:
        order = only(trace.events, "init")
        # The contract: `shop` omitting `views` moves nothing but its own module.
        assert order == [
            f"{app}.{kind}"
            for kind in KIND_CHAIN
            for app in apps
            if not (app == "shop" and kind == "views")
        ]
        assert_phases_do_not_interleave(order, kinds=("models", "urls"))
    finally:
        fw.shutdown()


# ── 4. The inversion is inexpressible ─────────────────────────────────────


def test_app_ordering_cannot_cross_a_kind_phase(tmp_path):
    """Every module of a kind shares one rank, and no two kinds share one.

    This is the structural reason a cross-phase inversion cannot be declared: the
    app axis only ever reaches the *second* element of the key. A future per-app
    ordering knob, or a per-app kind subset, can move a module inside its phase and
    nowhere else — and if one is ever built to do more, this test is what fails.
    """
    base = build(tmp_path, "tr_phase")
    trace = import_module("tr_phase")
    fw = framework(trace)
    fw.start(base)
    try:
        ranks: dict[str, set[int]] = {}
        for entry in fw.loader.ordered():
            ranks.setdefault(entry.kind, set()).add(entry.position[0])
        assert all(len(seen) == 1 for seen in ranks.values()), ranks
        by_kind = [next(iter(ranks[kind])) for kind in KIND_CHAIN]
        assert by_kind == sorted(by_kind)
        assert len(set(by_kind)) == len(by_kind)
    finally:
        fw.shutdown()


def test_declared_kind_cycle_is_refused_naming_the_cycle(tmp_path):
    """A cycle among declared kinds fails the start, before any module is imported."""
    base = build(tmp_path, "tr_kindcycle", kinds=("models",))
    fw = Framework(
        KindSpec("models", depends_on=("views",)),
        KindSpec("views", depends_on=("models",)),
    )
    with pytest.raises(CircularDependencyError) as exc:
        fw.start(base)
    message = str(exc.value)
    assert "models" in message and "views" in message
    assert fw.started is False


# ── 2.3 Hooks follow the same order, and reverse exactly ──────────────────


def test_hooks_fire_in_load_order_and_teardown_reverses_it(tmp_path):
    base = build(tmp_path, "tr_hooks")
    trace = import_module("tr_hooks")
    fw = framework(trace)

    fw.start(base)
    startup = [e for e in trace.events if not e.startswith("import:")]
    order = only(trace.events, "init")

    # Per module the kind's hook fires, then the module's own initialize().
    assert startup == [
        part for module in order for part in (f"hook:{module}", f"init:{module}")
    ]

    # A dependent kind's hook sees every app's contribution to the kind below.
    assert only(trace.events, "hook") == order

    trace.events.clear()
    fw.shutdown()

    # Teardown reverses the module order exactly; within a module the hook still
    # precedes the module's own function, so this is not a flat reversal.
    assert trace.events == [
        part
        for module in reversed(order)
        for part in (f"hookdown:{module}", f"down:{module}")
    ]


def test_order_is_stable_across_starts(tmp_path):
    """Two starts of one project in one process produce one order."""
    base = build(tmp_path, "tr_restart")
    trace = import_module("tr_restart")
    fw = framework(trace)

    fw.start(base)
    first = only(trace.events, "init")
    fw.shutdown()

    trace.events.clear()
    fw.start(base)
    try:
        assert only(trace.events, "init") == first
    finally:
        fw.shutdown()
