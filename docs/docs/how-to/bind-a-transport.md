# Bind a Transport

**How do I put my framework behind FastAPI (or anything else)?** The same way
[the tutorial](../learn/build-a-framework.md) bound stdlib `http.server`: a
loop over the registry. SPOC never chooses your transport — any library that
maps _name → callable_ binds in a few lines, and your components never learn
which one called them.

This page reuses the tutorial's project — rules, app, settings — and swaps
the surface. The FastAPI example needs `pip install fastapi` (and `uvicorn`
to serve it); nothing else on the page does.

## The project being bound

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


@route
def goodbye():
    return {"message": "That's the whole trick"}
```

```toml title="config/spoc.toml"
[spoc.apps]
development = ["apps.hello"]
```

## The binding — FastAPI edition

```python title="http_app.py"
"""An HTTP surface over the registry — the tutorial's serve.py, upgraded."""

from pathlib import Path

from fastapi import FastAPI

from framework import framework

BASE_DIR = Path(__file__).resolve().parent


def create_app():
    framework.start(BASE_DIR)
    app = FastAPI(title="hello-framework")
    for c in framework.registry.by_kind("routes"):
        app.add_api_route(
            f"/{c.namespace}/{c.object_name}", c.object, methods=["GET"]
        )
    return app


app = create_app()   # uvicorn http_app:app
```

Serve it for real with `uvicorn http_app:app`. To _see_ that the route table
came from the registry — no server needed:

```python title="main.py"
from http_app import app

print([r.path for r in app.routes if r.path.startswith("/hello")])
# ['/hello/greet', '/hello/goodbye']
```

You get FastAPI's whole world — OpenAPI docs at `/docs`, validation,
middleware — and your apps didn't change by a character.

## The same shape, other transports

- **A message socket**: iterate the same loop, subscribe each name, call the
  object on message arrival.
- **A worker loop**: resolve a callable by tag and schedule it however your
  queue likes.
- **A CLI**: the starter template's `surface.py`/`cli.py` pair is this
  pattern over argparse — `spoc init myproject --template starter` generates
  it working.

Next: [validate your settings](validate-settings.md).
