"""
    Framework
"""

import spoc

PLUGINS = ["commands", "models", "views"]

@spoc.singleton
class MyFramework:
    """Framework"""

    def init(
        self,
    ):
        """Class __init__ Replacement"""
        framework = spoc.App(plugins=PLUGINS)
                
        self.base_dir=framework.base_dir
        self.mode = framework.mode
        self.env=framework.config["env"]
        self.pyproject=framework.config["pyproject"]
        self.spoc=framework.config["spoc"]
        self.settings = framework.settings        
        self.component = framework.component
        self.extras = framework.extras
                
        self.keys = [
            "base_dir",
            "mode",
            "env",
            "pyproject",
            "spoc",
            "settings",
            "component",
            "extras",            
        ]