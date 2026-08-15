# Testing Your Project

`spoc.testing` ships with SPOC and gives you three pieces: build a throwaway
project, boot it in isolation, and try different modes. Nothing here touches
the kernel — and nothing you boot in a test leaks into the next one.

!!! note "One extra needed"
The tree builder and mode switcher _write_ TOML, which needs
`pip install "spoc[toml]"`. If it's missing, the error says exactly that.

## Build a throwaway project: `ProjectTree`

Describe a project as a dict — apps, modules, source — and materialize it in a
temp folder. Every test on this page shares one app module, kept in
`conftest.py`:

```python title="conftest.py"
MODELS = """
from spoc import component

@component(kind="models")
class Post:
    pass
"""
```

```python title="test_tree.py"
from conftest import MODELS
from spoc.testing import ProjectTree


def test_build_a_tree(tmp_path):
    tree = ProjectTree(apps={"blog": {"models": MODELS}})
    base = tree.build(tmp_path)  # writes config/spoc.toml, blog/, __init__.py...
    assert (base / "config" / "spoc.toml").exists()
```

Every declared app is auto-installed under the `development` mode; pass
`config={...}` to override any part of the `[spoc]` table.

!!! note "Why `component` and not a decorator from `framework.py`?"
A test tree has no `framework.py` — the test itself constructs the
framework. The `component` marker puts the same name tag on a block
without importing one, which is exactly what a throwaway app needs.

## Boot it safely: `isolated`

A context manager that boots a framework against a folder and — success or
failure — shuts it down and restores `sys.path` and `sys.modules`:

```python title="test_isolated.py"
from conftest import MODELS
from spoc.testing import ProjectTree, isolated


def test_boot_in_isolation(tmp_path):
    base = ProjectTree(apps={"blog": {"models": MODELS}}).build(tmp_path)

    with isolated(base, "models") as fw:
        record = fw.resolve("models:blog.post")
        assert record.namespace == "blog"
    # outside the block: framework stopped, imports restored, nothing leaked
```

Pass kinds and the scope builds the framework, or hand it a prebuilt one when
the declaration needs hooks or `KindSpec` details:
`isolated(base, framework=my_framework)`. Use `start=False` to get an inert
framework when the thing you're testing _is_ the boot.

## Try another mode: `mode`

```python title="test_modes.py"
from conftest import MODELS
from spoc.testing import ProjectTree, isolated, mode


def test_production_mode(tmp_path):
    base = ProjectTree(apps={"blog": {"models": MODELS}}).build(tmp_path)

    with mode(base, "production"):      # temporarily rewrites spoc.toml
        with isolated(base, "models") as fw:
            assert fw.config.project["mode"] == "production"
    # the file's original bytes are back
```

## With pytest: the fixtures

Install SPOC and the fixtures are just _there_ — no plugin registration, no
conftest wiring. The worked test is
[Test Your App](../how-to/test-your-app.md); what each fixture gives you:

| Fixture          | What it gives you                                          |
| ---------------- | ---------------------------------------------------------- |
| `spoc_tree`      | `ProjectTree(...).build(...)` under this test's `tmp_path` |
| `spoc_isolated`  | The `isolated` scope, as a factory                         |
| `spoc_framework` | Both at once: build a tree, get a started framework        |

Teardown always runs, even when the test fails — the next test starts from a
clean world.

To run every test on this page, type `pytest`. (The docs' own harness does the
same through a tiny entry point — that's how these examples stay green:)

```python title="main.py"
"""These docs run their own examples: pytest over the files above."""

import subprocess
import sys

raise SystemExit(subprocess.run([sys.executable, "-m", "pytest", "-q"]).returncode)
```

Next: [reading data files](formats.md).
