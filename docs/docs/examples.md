# The Storefront Example

The repository ships one complete, runnable reference project:
[`examples/`](https://github.com/hlop3z/spoc/tree/main/examples) — a tiny
storefront with three apps. The test suite boots it, so it can never drift
from the real kernel.

```
examples/
├── config/spoc.toml     # three modes, plugin declarations
├── framework.py         # four kinds: models, views, middleware, hooks
├── apps/
│   ├── auth/            # models:auth.user_account, models:auth.role, ...
│   ├── catalog/         # models:catalog.product, views:catalog.list_products
│   └── orders/          # views:orders.order_summary — resolves catalog at runtime
├── extras.py            # plugin-registered middleware and hooks
├── main.py              # boot, resolve, enumerate, shutdown
├── async_main.py        # the same boot through astart/ashutdown
├── http_app.py          # a web surface projected from the registry
└── data_app.py          # spoc.formats reading the data/ folder
```

## Run it

```bash
git clone https://github.com/hlop3z/spoc
cd spoc/examples
python main.py
```

```text
Ready: 8 components registered
Installed apps: ['apps.catalog', 'apps.orders', 'apps.auth']
Resolved: models:auth.user_account -> <class 'apps.auth.models.UserAccount'>
Order total: 15800 cents
 - hooks:extras.hook
 - middleware:extras.middleware
 - models:auth.role
 - models:auth.user_account
 ...
```

## What to look at

- **Cross-app calls without imports** — `apps/orders/views.py` computes an
  order total using the catalog's blocks, resolved by name tag at call time.
  The two apps share nothing but the grammar.
- **Plugins** — `extras.py` holds plain functions that `spoc.toml` registers
  into the `middleware` and `hooks` kinds. No decorator anywhere.
- **A surface as a projection** — `http_app.py` builds its routes purely by
  enumerating the registry, exactly the pattern the kernel is designed for.
- **One system, three modes** — every mode boots the same apps here;
  differences live in `config/.env/<mode>.toml`.
