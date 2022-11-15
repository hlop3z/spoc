<div id="terminal-extras" data-termynal></div>

```python title="apps/demo/middleware.py"
# -*- coding: utf-8 -*-
"""
    { Middleware }
"""

def on_event():
    print("Hello World (Middleware)")
```

!!! info "config/spoc.toml"

    Remember that we **registered** the middleware earlier.

```toml title="config/spoc.toml"
[spoc]
# ...

[spoc.extras]
before_server = ["demo.middleware.on_event"]
```
