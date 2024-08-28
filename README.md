# Welcome to **SPOC**

<img src="https://raw.githubusercontent.com/hlop3z/spoc/main/docs/docs/assets/images/title.png" alt="title-image" width="100%" />

---

**SPOC** is a foundational framework designed to create dynamic and adaptable **`frameworks`**. It involves defining a schema for your **project**(s) and building upon that schema to create a flexible and powerful Application.

---

## Links

- ### [PyPi](https://pypi.org/project/spoc)
- ### [Github](https://github.com/hlop3z/spoc)
- ### [Read the Documents](https://hlop3z.github.io/spoc/)

---

## Example

```python
from typing import Any
import spoc

MODULES = ["models", "views"]

class MyFramework(spoc.Base):
    components: Any
    plugins: Any

    def init(self):
        """__init__ Replacement"""
        app = spoc.init(MODULES)

        # Assign components and plugins from the initialized app
        self.components = app.components
        self.plugins = app.plugins

    @staticmethod
    def keys():
        """Define a list of keys relevant to the framework"""
        return ("components", "plugins")
```
