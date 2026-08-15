# Ship a Reusable App

**How do I publish an app someone else can install into _their_ framework?**
The one rule: a reusable app must not import its host's `framework.py` — it
can't know where that lives. The `spoc.component` marker puts the same name
tag on a block without importing anything of the host's:

```python title="apps/greetings/routes.py"
from spoc import component


@component(kind="routes")
def hello_from_a_package():
    return {"message": "installed, not written"}
```

The host installs it like any of their own apps — the dotted path under
`[spoc.apps]` is a normal import path, so a `pip install`-ed package works
exactly like a local folder:

```toml title="config/spoc.toml"
[spoc.apps]
development = ["apps.hello", "apps.greetings"]
```

```python title="framework.py"
import spoc

framework = spoc.Framework("routes")

route = framework.kind("routes")
```

```python title="apps/hello/routes.py"
from framework import route


@route
def greet():
    return {"message": "Hello from a framework you built"}
```

```python title="main.py"
from pathlib import Path

from framework import framework

BASE_DIR = Path(__file__).resolve().parent

framework.start(BASE_DIR)

for c in framework.registry.by_kind("routes"):
    print(c.identifier)
# routes:greetings.hello_from_a_package
# routes:hello.greet

framework.shutdown()
```

Both apps land on the same shelf, under their own namespaces — the host's
decorator and your marker are two spellings of the same tag.

What to put on the package's label:

- **Name the kinds you declare components of.** A host can only install you
  if their framework declares those kinds — the
  [default vocabulary](../learn/vocabulary.md) exists so you rarely need
  exotic ones.
- **Never assume a transport.** Your blocks get projected by whatever surface
  the host built — that's [their binding](bind-a-transport.md), not yours.

Next: [the command line](../tools/cli.md).
