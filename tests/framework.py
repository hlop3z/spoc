"""
    Framework
"""

import spoc

PLUGINS = ["commands"]

@spoc.singleton
class MyFramework:
    """Framework"""

    def init(
        self,
    ):
        """Class __init__ Replacement"""
        framework = spoc.App(plugins=PLUGINS)