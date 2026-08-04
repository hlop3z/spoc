# Plugins

Plugins are loadable references declared in `spoc.toml` — the way to pull in
objects that are *configured*, not discovered. Unlike components (found by
scanning app modules), plugins are explicit: a group name and a
`package.module.attribute` reference.

## Declaring

```toml
# config/spoc.toml
[spoc.plugins]
middleware = ["demo.extras.middleware", "auth.extras.audit"]
hooks      = ["demo.extras.hook"]
```

Group names are yours (`middleware`, `hooks`, `commands`, …); the kernel
attaches no meaning to them. References resolve against the import path —
apps in `apps/` work, as does anything else importable.

## Loading

Plugins load during `start()`, in declaration order, before app modules
initialize. A reference that cannot be resolved **fails start**, naming the
reference — never a silent skip:

```python
framework.start(BASE_DIR)

framework.plugins                                 # {"middleware": {...}, "hooks": {...}}
framework.plugins["hooks"]["demo.extras.hook"]    # the loaded object, unexecuted
```

The kernel loads and stores the objects; it never calls them. What a
"middleware" or "hook" *does* is defined by the surface you build on top.
