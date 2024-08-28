# Creating the **Project**

Let’s set up your project structure. . .

These essential folders act as organizational pillars for your project's components, resources, and functionality. They help maintain a logical arrangement, enhance code clarity, and simplify collaboration.

!!! warning

    In this example, we'll create everything within a single folder for simplicity. However, in a real-world scenario, you'll ideally want to separate your framework and your projects into distinct directories. This approach enhances modularity and makes your codebase easier to manage and maintain.

## Create the **`Folders`**

<!-- termynal -->

```bash
$ mkdir myproject
$ cd myproject
$ spoc-init
$ mkdir framework apps apps/demo
```

## Create the **`Files`**

Let’s set up the demo files

<!-- termynal -->

```bash
$ touch main.py
$ touch framework/__init__.py
$ touch framework/components.py
$ touch framework/framework.py
$ touch apps/demo/commands.py
$ touch apps/demo/models.py
$ touch apps/demo/views.py
```

---

## Project Structure

```text
myproject/               --> Root directory of your project
|
|-- config/              --> Directory for configuration files
|   |-- __init__.py
|   |-- settings.py      --> Python settings file
|   |-- spoc.toml        --> TOML configuration file
|   `-- .env/            --> Directory for environment-specific settings
|       |-- development.toml
|       |-- production.toml
|       `-- staging.toml
|
|-- framework/           --> Directory for framework-related files
|   |-- __init__.py
|   |-- components.py    --> Framework components file
|   `-- framework.py     --> Main framework file
|
|-- apps/                --> Directory for your application modules
|   |-- ...
|   `-- demo/            --> Example module
|       |-- __init__.py  --> Makes the folder a Python package
|       |-- commands.py  --> Contains command functions
|       |-- models.py    --> Contains model definitions
|       `-- views.py     --> Contains view definitions
|
|-- main.py              --> Entry point for the application
|
`-- etc...
```

---

## Configuring **SPOC** with TOML

Define your project settings using a TOML configuration file:

```toml title="myproject/config/spoc.toml"
# Application Configuration
[spoc]
mode = "development" # options: development, staging, production
debug = true

# Installed Apps by Mode
[spoc.apps]
production = ["demo"]
development = []
staging = []

# Additional Components (Plugins and Hooks)
[spoc.plugins]
```

## Python **Settings** Configuration

Configure settings using a Python file:

```python title="myproject/config/settings.py"
# -*- coding: utf-8 -*-
"""
Settings
"""

import pathlib

# Base Directory
BASE_DIR = pathlib.Path(__file__).parents[1]

# Installed Apps
INSTALLED_APPS: list  = ["demo"]

# Extra Methods
PLUGINS: dict = {}
```

---

## Setting Up the **Framework**

=== "Framework"

    ```python title="framework/__init__.py"
    # -*- coding: utf-8 -*-
    """
    Framework
    """

    from typing import Any
    import spoc

    MODULES = ["commands", "models", "views"]

    class MyFramework(spoc.Base):
        """My Framework"""

        components: Any
        plugins: Any

        def init(self):
            """Class __init__ Replacement"""
            app = spoc.init(MODULES)

            # Parts
            self.components = app.components
            self.plugins = app.plugins

        @staticmethod
        def keys():
            return ("components", "plugins")
    ```

=== "Components"

    ```python title="framework/components.py"
    # -*- coding: utf-8 -*-
    """
    Components
    """

    from typing import Any
    import spoc

    components = spoc.Components()
    components.add("view")
    components.add("command", {"is_click": True})

    # Define your components.
    def command(obj: Any = None):
        """Command Component"""
        components.register("command", obj)
        return obj


    def view(obj: Any = None):
        """View Component"""
        components.register("view", obj)
        return obj
    ```

=== "Initialization"

    ```python title="framework/__init__.py"
    # -*- coding: utf-8 -*-
    """
    Module Initialization
    """

    from .components import components, command, view
    from .framework import MyFramework
    ```

---

## **Testing** the Framework

```python title="main.py"
# -*- coding: utf-8 -*-
"""{ Testing } Read The Docs"""

from framework import MyFramework

app = MyFramework()

# Print components groups
print(app.components.__dict__.keys())

# Print plugin groups
print(app.plugins.keys())

# Execute the registered command
app.components.commands["demo.hello_world"].object()
```

---

<!-- termynal -->

```
$ python main.py
> dict_keys(['commands', 'models', 'views'])
> dict_keys(['middleware', 'on_startup', 'on_shutdown'])
> Hello World (Commands)
```
