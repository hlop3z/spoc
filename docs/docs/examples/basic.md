# Basic Example

The complete project from the repository's `examples/` directory: two kinds,
four apps, the mode cascade, and an HTTP surface projected from the
registry.

## Layout

```
examples/
├── apps/
│   ├── __init__.py                      # apps/ is a package
│   ├── auth/       models.py            (production app)
│   ├── another/    models.py, views.py  (staging app)
│   ├── other/      models.py, views.py  (development app)
│   └── demo/       models.py, views.py  (development app)
├── config/
│   ├── spoc.toml        # the only file the kernel reads
│   └── settings.py      # user-owned; SPOC never imports it
├── framework/
│   └── framework.py     # the whole framework definition
├── main.py
└── http_app.py          # routes generated from the registry
```

`config/spoc.toml` declares the apps as dotted module paths, imported
exactly as written — the namespace is the final segment:

```toml
[spoc.apps]
production  = ["apps.auth"]
staging     = ["apps.another"]
development = ["apps.demo", "apps.other"]
```

## The framework definition

`framework/framework.py` — the entire thing:

```python
import spoc

framework = spoc.Framework("models", spoc.KindSpec("views", depends_on=("models",)))

model = framework.kind("models")
view = framework.kind("views")
```

## Declaring components

`apps/auth/models.py` — the identifier is derived from the class name:

```python
import dataclasses as dc
from framework.framework import model

@dc.dataclass
@model
class UserAccount:          # → models:auth.user_account
    id: int
    name: str
```

`apps/demo/views.py` — functions work the same way:

```python
from framework.framework import view

@view
def list_posts():
    return {"posts": []}
```

## Starting and resolving

`main.py`:

```python
from pathlib import Path
from framework.framework import framework

BASE_DIR = Path(__file__).resolve().parent

@framework.on_ready
def announce(registry):
    print(f"Ready: {len(registry)} components registered")

framework.start(BASE_DIR)

record = framework.resolve("models:auth.user_account")
print(record.identifier, "->", record.object)

for component in framework.registry:
    print(" -", component.identifier)

framework.shutdown()
```

Output:

```
Ready: 7 components registered
Installed apps: ['apps.demo', 'apps.other', 'apps.another', 'apps.auth']
models:auth.user_account -> <class 'apps.auth.models.UserAccount'>
 - models:auth.role
 - models:auth.user_account
 - models:demo.comment_thread
 - models:demo.post
 - models:other.user_account
 - views:demo.get_post
 - views:demo.list_posts
```

## Projecting an HTTP surface

`http_app.py` starts the framework, then builds its routes **purely by
enumerating the registry** — no kernel internals involved:

```python
from pathlib import Path
from framework.framework import framework

if not framework.started:
    framework.start(Path(__file__).resolve().parent)

def build_routes(registry):
    return [
        {
            "method": "GET",
            "path": f"/{record.namespace}/{record.object_name}",
            "endpoint": record.object,
            "name": record.identifier,
        }
        for record in registry.by_kind("views")
    ]

def create_app():
    from fastapi import FastAPI   # a dev dependency — never the kernel's

    app = FastAPI()
    for route in build_routes(framework.registry):
        app.add_api_route(route["path"], route["endpoint"],
                          methods=[route["method"]], name=route["name"])
    return app
```

```
$ python http_app.py
GET  /demo/get_post              <- views:demo.get_post
GET  /demo/list_posts            <- views:demo.list_posts
```

The same `build_routes` works for Robyn, a CLI, or any other surface — the
registry record is the whole contract.
