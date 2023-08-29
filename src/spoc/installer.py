import pathlib
from types import SimpleNamespace

SETTINGS_TEXT = '''
# -*- coding: utf-8 -*-
"""
    { Settings }
"""

import pathlib

# Base Directory
BASE_DIR = pathlib.Path(__file__).parents[1]
'''

CONFIG_TEXT = '''
# -*- coding: utf-8 -*-
"""
    { Config }
"""

from . import settings
'''


SPOC_TEXT = """
[spoc]
mode = "custom" # options: custom, development, production, staging
custom_mode = "development"

# Modes
[spoc.apps]
production = []
development = []
staging = []

# Extras
[spoc.extras]
"""


def create_base():
    import __main__

    root_dir = pathlib.Path(__main__.__file__).parent
    install_helper = SimpleNamespace()

    install_helper.config_dir = root_dir / "config"
    install_helper.config_file = install_helper.config_dir / "__init__.py"
    install_helper.settings_file = install_helper.config_dir / "settings.py"
    install_helper.spoc_file = install_helper.config_dir / "spoc.toml"

    install_helper.config_dir.mkdir(exist_ok=True)

    if not install_helper.config_file.exists():
        with open(install_helper.config_file, "w", encoding="utf-8") as file:
            file.write(CONFIG_TEXT)

    if not install_helper.settings_file.exists():
        with open(install_helper.settings_file, "w", encoding="utf-8") as file:
            file.write(SETTINGS_TEXT)

    if not install_helper.spoc_file.exists():
        with open(install_helper.spoc_file, "w", encoding="utf-8") as file:
            file.write(SPOC_TEXT)
