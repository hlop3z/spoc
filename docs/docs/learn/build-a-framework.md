# Build a Framework

The landing page claims you can build your own framework in about five lines
of rules. This page is where you do it — from an empty folder to a real HTTP
framework you author, in four small files, with **nothing installed but
`spoc`**. At the end, `curl` talks to it.

Every file below is complete — copy each one exactly, and the docs' own test
suite runs this page the same way, so it cannot drift.

## 0. An empty folder

```bash
mkdir hello-framework
cd hello-framework
pip install spoc
```

## 1. Your rules

One kind of block: a **route** — a function a web surface exposes. That
declaration, and the decorator your apps will import, is the entire
framework definition. (The decorator's name is yours to choose — `route`
reads well for one-at-a-time decorating.)

```python title="framework.py"
import spoc

framework = spoc.Framework("routes")

route = framework.kind("routes")
```

## 2. Your first app

A folder, and one file named after the kind. The function's tag is derived
for you: `greet` in app `hello` becomes `routes:hello.greet`.

```python title="apps/hello/routes.py"
from framework import route


@route
def greet():
    return {"message": "Hello from a framework you built"}
```

## 3. Your settings

Install the app:

```toml title="config/spoc.toml"
[spoc.apps]
development = ["apps.hello"]
```

## 4. Your transport

Here is the part most frameworks hide from you. A web framework is a loop:
take every registered block, give it a URL, hand requests to it. SPOC already
holds every block with a three-part name tag — so the URL scheme falls out of
the registry: `/{namespace}/{object_name}`.

```python title="serve.py"
"""The transport: stdlib http.server, projecting the registry."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from framework import framework


def build_routes():
    return {
        f"/{c.namespace}/{c.object_name}": c.object
        for c in framework.registry.by_kind("routes")
    }


class Handler(BaseHTTPRequestHandler):
    routes = {}

    def do_GET(self):
        handler = self.routes.get(self.path)
        if handler is None:
            self.send_error(404, f"no route {self.path} — try {sorted(self.routes)}")
            return
        body = json.dumps(handler()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the terminal quiet for the tutorial
        pass


def serve(port):
    Handler.routes = build_routes()
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Serving on http://127.0.0.1:{server.server_port}", flush=True)
    server.serve_forever()
```

Note what `serve.py` never does: it doesn't import your app, and it doesn't
keep a route table of its own. It asks the shelf.

## 5. The start button

```python title="main.py"
import sys
from pathlib import Path

from framework import framework
from serve import serve

BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    framework.start(BASE_DIR)
    serve(port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
```

## 6. Run it

```bash
python main.py
```

```text
Serving on http://127.0.0.1:8000
```

And from another terminal:

```bash
curl http://127.0.0.1:8000/hello/greet
```

```text
{"message": "Hello from a framework you built"}
```

That response came from a function *you* tagged, found by rules *you* wrote,
served by a loop *you* can read in one screen.

## 7. The payoff: add a function, get an endpoint

This is the moment that makes it a framework and not a script. Add one more
function — touch nothing else:

```python title="apps/hello/routes.py"
from framework import route


@route
def greet():
    return {"message": "Hello from a framework you built"}


@route
def goodbye():
    return {"message": "That's the whole trick"}
```

Restart, and the URL already exists — no route table was edited, because
there is no route table to edit:

```bash
curl http://127.0.0.1:8000/hello/goodbye
```

```text
{"message": "That's the whole trick"}
```

Mistype a URL and the 404 names every route that *does* exist — the loud-
failure habit, inherited by your framework for free.

## What you just built

- `framework.py` — the rules (5 lines).
- `apps/hello/routes.py` — a contributor's world: write a function, tag it.
- `serve.py` — the surface: one loop over the registry. Swap it for FastAPI,
  a CLI, or a worker queue and the apps never change — the
  [transport how-to](../how-to/bind-a-transport.md) shows that exact swap.
- `main.py` — the start button.

Grow it from here: give routes a
[metadata form](framework.md) (`Route(path=…, method=…)`) when the derived
URL scheme stops being enough, split blocks across
[more apps and modes](apps.md), and open shared clients with the
[resource recipe](vocabulary.md).

Next: [the command line](../tools/cli.md).
