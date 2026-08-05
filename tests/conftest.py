"""
Shared suite machinery, backed by the shipped harness (`spoc.testing`).

The suite proves the harness by depending on it: import-state isolation and
project-tree building live in `spoc.testing`, not in per-file copies. Tests
that deliberately exercise raw layouts (config edge cases, malformed trees)
keep their explicit setup.
"""

import sys
from pathlib import Path
from typing import Any

import pytest

from spoc.testing import ProjectTree, import_state

MODELS_BODY = """
    from spoc.core.declaration import component

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
