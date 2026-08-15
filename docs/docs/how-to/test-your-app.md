# Test Your App

**How do I write a test that boots my app?** Install SPOC and the pytest
fixtures are just _there_ — no plugin registration, no conftest wiring. One
fixture, `spoc_framework`, builds a throwaway project and hands you a started
framework; teardown always runs, so nothing leaks into the next test.

```python title="conftest.py"
MODELS = """
from spoc import component

@component(kind="models")
class Post:
    pass
"""
```

```python title="test_app.py"
from conftest import MODELS


def test_blog_registers_a_post(spoc_framework):
    fw = spoc_framework("models", apps={"blog": {"models": MODELS}})
    assert fw.resolve("models:blog.post").object_name == "post"
```

Run it:

```bash
pytest
```

## The pieces, used separately

`spoc_framework` is one call over two smaller fixtures, and both are handed to
you as well. `spoc_tree` builds a project tree under the test's `tmp_path`
without booting it; `spoc_isolated` boots any tree inside an isolation scope
and tears everything down — framework state, `sys.path`, imported modules — on
the way out:

```python title="test_pieces.py"
from conftest import MODELS


def test_a_prebuilt_tree_boots_in_isolation(spoc_tree, spoc_isolated):
    base = spoc_tree(apps={"blog": {"models": MODELS}}, name="pieces")
    with spoc_isolated(base, "models") as fw:
        assert [c.identifier for c in fw.registry] == ["models:blog.post"]
    assert not fw.started  # nothing outlives the scope
```

Splitting them matters the moment one test needs two projects, a tree it
edits between boots, or a boot it never wants — `spoc_isolated(base, "models",
start=False)` yields an inert framework for tests that exercise boot itself,
and `framework=` takes a prebuilt declaration when hooks or `KindSpec`s are
the thing under test.

```python title="main.py"
"""These docs run their own examples: pytest over the files above."""

import subprocess
import sys

raise SystemExit(subprocess.run([sys.executable, "-m", "pytest", "-q"]).returncode)
```

## In CI

The fixtures test your app's _behavior_; `spoc check` tests its _structure_ —
settings, imports, dependency cycles, name collisions — without running any of
it ([The Command Line](../tools/cli.md)). They catch different mistakes, and
the second is one line:

```bash
pytest        # behavior: your tests, on the fixtures above
spoc check    # structure: dry-boot, exit 0 when clean
```

Two things worth knowing before you write more:

- The tree uses `spoc.component`, not a decorator from `framework.py` — a
  throwaway app has no `framework.py` to import, and the marker puts the same
  name tag on a block without one.
- When the fixtures aren't enough — mode switching, custom layouts — the
  pieces they're made of (`ProjectTree`, `isolated`, `mode`) are all public:
  see [Testing Your Project](../tools/testing.md).

Next: [ship a reusable app](ship-a-reusable-app.md).
