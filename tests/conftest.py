"""
Shared suite machinery, backed by the shipped harness (`spoc.testing`).

The suite proves the harness by depending on it: import-state isolation and
project-tree building live in `spoc.testing`, not in per-file copies. Tests
that deliberately exercise raw layouts (config edge cases, malformed trees)
keep their explicit setup.
"""

import socket
import sys
from pathlib import Path
from typing import Any

import pytest

from spoc.testing import ProjectTree, import_state

MODELS_BODY = """
    from spoc import component

    @component(kind="models")
    class Post:
        ...
"""


@pytest.fixture
def clean_sys_path_and_modules():
    """Keep app imports from leaking between tests.

    Not autouse: it removes *every* module imported during a test, which would
    also strip third-party modules other suites import lazily (the formats
    suite's query engine) and orphan their cached exception classes. Modules
    that boot apps opt in with
    ``pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")``.
    """
    with import_state():
        yield


@pytest.fixture
def no_sockets(monkeypatch: pytest.MonkeyPatch):
    """Fail any test that tries to open a network connection.

    The retrieval modules split into `RevisionResolver`, `Fetcher`, and `Cache`
    precisely so the whole remote path is exercisable without a server. That
    claim is worth enforcing rather than restating: without this, a test that
    quietly reached the network would still pass, and would then fail in CI or
    on a plane for reasons unrelated to what it was testing.

    Not autouse: the suite builds and boots real projects, and a blanket ban
    would be a claim about all of them rather than about the modules that make
    it. Modules opt in with
    ``pytestmark = pytest.mark.usefixtures("no_sockets")``.
    """

    def refuse(*args: object, **kwargs: object):
        raise AssertionError(
            "this test opened a socket; the remote path is meant to be "
            "exercisable entirely against in-memory ports"
        )

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    yield


def make_project(
    tmp_path: Path,
    app: str,
    models_body: str = MODELS_BODY,
    config: dict[str, Any] | None = None,
    extra_modules: dict[str, str] | None = None,
) -> Path:
    """Build a one-app project and make it importable, as an entry point would.

    Boot-style tests call ``fw.start(base)`` themselves, so the path insertion
    lives here rather than in an `isolated` scope; the autouse fixture above
    restores it.
    """
    base = ProjectTree(
        apps={app: {"models": models_body, **(extra_modules or {})}},
        config=config or {},
    ).build(tmp_path, f"proj_{app}")
    sys.path.insert(0, str(base))
    return base
