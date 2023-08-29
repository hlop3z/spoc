**Crafting Your Configuration Files**

In the process of setting up your project, crafting configuration files is a pivotal step. These files contain settings, parameters, and options that tailor the behavior of your application to your specific needs. Configuration files ensure that your application runs seamlessly across various environments and can be easily customized without altering the codebase.

**Consider these important configuration files:**

**`spoc.toml`**: This file, named after the S.P.O.C framework, houses core configuration settings. It's where you define project-wide preferences, such as installed apps, framework extras, and global options. Modifying this file allows you to fine-tune the behavior of your framework.

**`settings.py`**: A common configuration file in Python projects, it contains application-specific settings. These settings might include database configurations, security options, logging preferences, and more. Separating these settings from your codebase promotes modularity and maintainability.

<div id="terminal-config" data-termynal></div>

## File: **spoc.toml**

```toml title="config/spoc.toml"
[spoc]
mode = "custom"
custom_mode = "development"

# Mode(s)
[spoc.apps]
production = []
development = ["demo"]
staging = []

[spoc.extras]
before_server = ["demo.middleware.on_event"]
```

## File: **settings.py** (**`custom`**)

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

## File: **development.toml**

- **`development`**
- **`production`**
- **`staging`**

```toml title="config/.env/development.toml"
[env]
DEBUG       = "yes"
SECRET_KEY  = "api-not-secure-key-09d25e094faa6ca2556c"
```
