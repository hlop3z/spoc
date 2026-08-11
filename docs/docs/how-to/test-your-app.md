# Test Your App

**How do I write a test that boots my app?** Install SPOC and the pytest
fixtures are just *there* — no plugin registration, no conftest wiring. One
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

```python title="main.py"
"""These docs run their own examples: pytest over the files above."""

import subprocess
import sys

raise SystemExit(subprocess.run([sys.executable, "-m", "pytest", "-q"]).returncode)
```

Two things worth knowing before you write more:

- The tree uses `spoc.component`, not a decorator from `framework.py` — a
  throwaway app has no `framework.py` to import, and the marker puts the same
  name tag on a block without one.
- When the fixture isn't enough — prebuilt trees, inert boots, mode
  switching — the pieces it's made of (`ProjectTree`, `isolated`, `mode`) are
  all public: see [Testing Your Project](../tools/testing.md).

Next: [ship a reusable app](ship-a-reusable-app.md).
