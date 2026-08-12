"""
Producing a projection: the collect-only boot, and what it yields.

Describing a project stops one phase earlier than starting it. :meth:`Framework.start`
runs discovery and *then* initializes modules; describing reuses the first half
and stops, so a project whose startup hook opens a database connection is still
describable on a laptop that has no database. A discovery failure is still a
failure — an unimportable app module or invalid configuration raises the
kernel's own error, unchanged, because a description that quietly omitted what
it could not import would be worse than none.

This module owns the collect-only boot for every surface that needs one. The
stub generator boots through :func:`collected` too, which is what keeps two
descriptions of one registry from disagreeing about what a boot even is.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ..core.exceptions import SpocError
from ..framework import Framework
from ..locate import DEFAULT_FRAMEWORK_REF, locate_framework
from ..testing import import_state
from .document import ComponentEntry, Projection

__all__ = ["collected", "project", "projection_of"]


@contextmanager
def collected(framework: Framework, base_dir: Path | str) -> Iterator[Framework]:
    """Run `framework`'s discovery phase, yield it, and reset it afterwards.

    Discovery runs; initialization does not. The framework returns to its
    pre-description state before this exits, on the failure path as well as the
    success one, so describing a project is never a way to half-start it.
    """
    if framework.started:
        raise SpocError(
            "Cannot describe a started framework: describing runs its own "
            "collect-only boot and would race the running one"
        )
    # The collect-only half of start(). Reached through an Any-typed local
    # because it is deliberately private: no caller outside this package may
    # split a boot in half, and this is the one place that does.
    boot: Any = framework._boot_discovery
    try:
        boot(Path(base_dir))
        yield framework
    finally:
        # Leave nothing behind that an ordinary start would not have.
        framework._reset()


def projection_of(framework: Framework) -> Projection:
    """Describe an already-discovered `framework` as a projection.

    ``Registry.all`` sorts by identifier, so emission order is a property of the
    grammar rather than of declaration order, load order, or filesystem layout.
    """
    return Projection(
        kinds=framework.kinds,
        components=tuple(
            ComponentEntry.from_component(record) for record in framework.registry.all()
        ),
    )


def project(
    base_dir: Path | str, framework_ref: str = DEFAULT_FRAMEWORK_REF
) -> Projection:
    """Describe the project at `base_dir`, importing and registering nothing
    that outlives the call.

    The isolation scope is the same one every other dry-boot operation uses:
    ``sys.path`` and ``sys.modules`` are restored, and the framework is reset,
    before this returns.
    """
    base = Path(base_dir)
    with import_state():
        sys.path.insert(0, str(base))
        framework = locate_framework(framework_ref)
        with collected(framework, base) as discovered:
            return projection_of(discovered)
