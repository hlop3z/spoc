"""
Framework
"""

from typing import Any

import spoc

PLUGINS = ["commands", "models", "views"]


class MyFramework(spoc.Base):
    """My Framework"""

    components: Any
    extras: Any
    keys: Any

    def init(self):
        """Class __init__ Replacement"""
        app = spoc.init(PLUGINS)

        self.components = app.components
        self.extras = app.extras

        self.keys = [
            "components",
            "extras",
        ]
