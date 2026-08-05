"""
Test harness for SPOC applications — a contained subpackage.

The kernel never imports this; importing :mod:`spoc` never loads it. The
harness composes the kernel's *public* contracts only, so it is usable from
any test runner or from a plain script:

.. code-block:: python

    from pathlib import Path
    from spoc.testing import ProjectTree, isolated, mode

    tree = ProjectTree(apps={"blog": {"models": MODELS_SOURCE}})
    base = tree.build(Path(tmp))

    with isolated(base, "models") as fw:
        record = fw.resolve("models:blog.post")

Pytest surfaces the same pieces as fixtures through the in-distribution
plugin (:mod:`spoc.testing.plugin`); nothing here requires pytest.
"""

from .core import MissingDependencyError, import_state, isolated, mode
from .tree import ProjectTree

__all__ = [
    # Isolation
    "isolated",
    "import_state",
    "mode",
    # Tree building
    "ProjectTree",
    # Errors
    "MissingDependencyError",
]
