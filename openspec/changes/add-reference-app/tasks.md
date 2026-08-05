## 1. Domain reshape

- [x] 1.1 Replace `demo`/`other`/`another` with `catalog` (Product + views), `orders` (Order + a view resolving `models:catalog.product` through the registry at call time), keep `accounts`/`auth` naming consistent; update `config/spoc.toml` app lists and plugins accordingly
- [x] 1.2 Delete the superseded toy apps (Rule 5) and sweep `examples/` docstrings for stale names

## 2. Lifecycles and projection

- [x] 2.1 Add `async_main.py` — coroutine `on_startup`/`on_shutdown` hooks, booted with `astart`, over the same tree
- [x] 2.2 Keep `http_app.py` deriving routes from the registry; point it at the new domain

## 3. Suite and CI

- [x] 3.1 `tests/test_examples.py`: boot the real `examples/` tree (import_state + the example's own declaration) — registry contents, cross-namespace resolution, plugins, route projection, both entries; FastAPI parts via importorskip
- [x] 3.2 CI + Taskfile: install the `examples` group so the projection test genuinely runs in CI
- [x] 3.3 Full validation per `.canon/checks.md`

## 4. Docs

- [x] 4.1 Update the examples docs page to the storefront domain; `mdlinks` clean
