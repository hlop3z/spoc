"""
Definition-of-done example: HTTP routes generated purely by enumerating the
SPOC registry through the public API. Nothing here imports kernel internals —
only `framework.registry` records are read.

`build_routes` is surface-agnostic (works with FastAPI, Robyn, or anything
else). `create_app` wires the same routes into FastAPI when it is installed
(a dev dependency of the examples — never of the kernel).

Run:  uvicorn http_app:app  (from the examples/ directory, fastapi installed)
"""

from pathlib import Path
from typing import Any

from framework.framework import framework

if not framework.started:
    framework.start(Path(__file__).resolve().parent)


def build_routes(registry: Any) -> list[dict[str, Any]]:
    """Derive an HTTP route table from registry records alone."""
    routes = []
    for record in registry.by_kind("views"):
        routes.append(
            {
                "method": "GET",
                "path": f"/{record.namespace}/{record.object_name}",
                "endpoint": record.object,
                "name": record.identifier,
            }
        )
    return routes


def create_app():
    """Build a FastAPI app whose routes all come from the registry."""
    from fastapi import FastAPI  # dev dependency, not a kernel dependency

    app = FastAPI(title="SPOC registry projection")
    for route in build_routes(framework.registry):
        app.add_api_route(
            route["path"],
            route["endpoint"],
            methods=[route["method"]],
            name=route["name"],
        )
    return app


if __name__ == "__main__":
    for r in build_routes(framework.registry):
        print(f"{r['method']:4} {r['path']:30} <- {r['name']}")
else:
    try:
        app = create_app()
    except ImportError:
        app = None
