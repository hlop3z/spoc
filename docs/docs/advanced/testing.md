# Testing Your App

SPOC ships its test harness in the box: `spoc.testing` is a contained
subpackage — the kernel never imports it, importing `spoc` never loads it —
that gives your suite the three pieces every SPOC project otherwise
hand-rolls: an **isolation scope**, a **project-tree builder**, and a
**mode override**. With pytest, the same pieces arrive as fixtures
automatically.

## The isolation scope

`isolated()` boots a framework against a project tree and guarantees
teardown — the framework is shut down and every piece of process state the
boot touched (`sys.path`, `sys.modules`) is restored, whether the block exits
normally or raises. Consecutive scopes observe nothing from each other.

```python
from spoc.testing import isolated

with isolated(base_dir, "models") as fw:
    record = fw.resolve("models:blog.post")
```

Pass kind names and the scope constructs the framework, or hand it a prebuilt
one when you need to configure declaration first (hooks, `KindSpec`); add
`start=False` to receive it inert and boot inside the scope yourself:

```python
fw = spoc.Framework(KindSpec("models", on_startup=hook))
with isolated(base_dir, framework=fw, start=False) as inert:
    inert.start(base_dir)
```

No test runner is involved — the scope works in a plain script. Suites that
manage framework lifecycles themselves can use the underlying
`spoc.testing.import_state()` scope, which restores `sys.path` /
`sys.modules` and nothing else.

## Building project trees

`ProjectTree` materializes a bootable project from a declaration — apps,
their modules' source, and config entries — so a test never spells out the
on-disk layout:

```python
from spoc.testing import ProjectTree

MODELS = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Post:
        ...
"""

base = ProjectTree(apps={"blog": {"models": MODELS}}).build(tmp_path)
```

By default every declared app is listed under the `development` mode;
`config=` entries merge over the generated `[spoc]` table:

```python
ProjectTree(
    apps={"blog": {"models": MODELS}, "shop": {"models": ORDER}},
    config={"mode": "staging", "apps": {"staging": ["blog", "shop"]}},
)
```

TOML emission uses the `toml` extra (`pip install "spoc[toml]"`); without it
the builder refuses loudly and names the extra — nothing in the kernel is
affected.

## Overriding the mode

`mode()` rewrites `spoc.mode` in the tree's `spoc.toml` for the duration of
the block and restores the file's original bytes on exit. Boot inside the
scope — the kernel reads the file at `start()`:

```python
from spoc.testing import isolated, mode

with mode(base_dir, "staging"), isolated(base_dir, "models") as fw:
    assert fw.config.project["mode"] == "staging"
```

## Pytest fixtures

Installing `spoc` next to pytest registers the plugin automatically — no
conftest entry, nothing to configure. Three fixtures wrap the pieces above:

| Fixture          | What it gives your test                                          |
| ---------------- | ---------------------------------------------------------------- |
| `spoc_tree`      | `ProjectTree` factory bound to this test's `tmp_path`            |
| `spoc_isolated`  | the `isolated()` scope, as a factory                             |
| `spoc_framework` | one call: build a tree, boot a framework, tear down after the test |

```python
def test_post_registers(spoc_framework):
    fw = spoc_framework("models", apps={"blog": {"models": MODELS}})
    assert fw.resolve("models:blog.post").identifier == "models:blog.post"
```

Teardown runs even when the test fails — the next test sees a clean process.

SPOC's own suite runs on this harness, so every guarantee above is pinned by
the same tests that pin the kernel.
