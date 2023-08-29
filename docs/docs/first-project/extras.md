As you venture further into harnessing the power of the **S.P.O.C** framework, mastering the creation of extra methods opens doors to extending and customizing your application's capabilities. Extras are a mechanism for augmenting your framework with additional functionalities beyond the core components.

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

    Remember to **register** the middleware.

```toml title="config/spoc.toml"
[spoc]
# ...

[spoc.extras]
before_server = ["demo.middleware.on_event"]
```
