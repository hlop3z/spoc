"""
Pytest fixtures over the harness — thin adapters, no logic of their own.

Registered through the ``pytest11`` entry point in ``pyproject.toml``, so a
downstream project gets these by installing ``spoc`` alongside pytest —
nothing to configure. Only pytest ever imports this module (the entry point
is inert metadata otherwise), so the top-level ``import pytest`` never runs
in a runtime environment.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, ExitStack
from itertools import count
from pathlib import Path
from typing import Any

import pytest

from .core import isolated
from .tree import ProjectTree

__all__ = ["spoc_framework", "spoc_isolated", "spoc_tree"]


@pytest.fixture
def spoc_tree(tmp_path: Path) -> Callable[..., Path]:
    """Build a project tree under this test's ``tmp_path``.

    A factory so one test can build several independent trees::

        base = spoc_tree(apps={"blog": {"models": MODELS}})
    """

    def build(
        apps: dict[str, dict[str, str]] | None = None,
        config: dict[str, Any] | None = None,
        name: str = "project",
    ) -> Path:
        return ProjectTree(apps=apps or {}, config=config or {}).build(tmp_path, name)

    return build


@pytest.fixture
def spoc_isolated() -> Callable[..., AbstractContextManager[Any]]:
    """The :func:`spoc.testing.isolated` scope, as a fixture-provided factory.

    ::

        with spoc_isolated(base, "models") as fw:
            fw.resolve("models:blog.post")
    """
    return isolated


@pytest.fixture
def spoc_framework(spoc_tree, spoc_isolated) -> Iterator[Callable[..., Any]]:
    """One-call convenience: build a tree and yield a started framework.

    ::

        fw = spoc_framework("models", apps={"blog": {"models": MODELS}})
    """
    trees = count()
    with ExitStack() as stack:

        def boot(
            *kinds: Any,
            apps: dict[str, dict[str, str]] | None = None,
            config: dict[str, Any] | None = None,
        ) -> Any:
            base = spoc_tree(apps=apps, config=config, name=f"project{next(trees)}")
            return stack.enter_context(spoc_isolated(base, *kinds))

        yield boot
