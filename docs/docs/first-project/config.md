<div id="terminal-config" data-termynal></div>

## File: **settings.py**

```python title="config/settings.py"
# -*- coding: utf-8 -*-
"""
    { Settings }
"""

import pathlib

# Base Directory
BASE_DIR = pathlib.Path(__file__).parents[1]

# Installed Apps
INSTALLED_APPS = [] # works only with <mode = "custom">
```

## File: **spoc.toml**

```toml title="config/spoc.toml"
[spoc]
mode = "development" # custom
# custom_mode = "development"

# Mode(s)
[spoc.apps]
production = []
development = ["demo"]
staging = []

[spoc.extras]
before_server = ["demo.middleware.on_event"]
```

## File: **development.toml**

```toml title="config/.env/development.toml"
[env]
DEBUG       = "yes"
SECRET_KEY  = "api-not-secure-key-09d25e094faa6ca2556c"
```
