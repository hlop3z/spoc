# The Storefront Example

The repository ships one complete, runnable reference project:
[`examples/`](https://github.com/hlop3z/spoc/tree/main/examples) — a tiny
storefront with three apps. The test suite boots it, so it can never drift
from the real kernel.

```
examples/
├── config/spoc.toml     # three modes, plugin declarations
├── framework.py         # five kinds: models, views, resources, middleware, hooks
├── apps/
│   ├── auth/            # models:auth.user_account, models:auth.role, ...
│   ├── catalog/         # models, views, and resources:catalog.search_index
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
Ready: 10 components registered
Installed apps: ['apps.catalog', 'apps.orders', 'apps.auth']
Resolved: models:auth.user_account -> <class 'apps.auth.models.UserAccount'>
Order total: 15800 cents
Search hit: mouse
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
- **A resource with a lifecycle** — `apps/catalog/resources.py` declares a
  search index the `resources` kind opens at start and closes at shutdown;
  `views:catalog.find_product` reaches it through the registry mid-call. The
  full recipe is in [The Default Vocabulary](learn/vocabulary.md).
- **Plugins** — `extras.py` holds plain functions that `spoc.toml` registers
  into the `middleware` and `hooks` kinds. No decorator anywhere.
- **A surface as a projection** — `http_app.py` builds its routes purely by
  enumerating the registry, exactly the pattern the kernel is designed for.
- **One system, three modes** — every mode boots the same apps here;
  differences live in `config/.env/<mode>.toml`.
