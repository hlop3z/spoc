import pathlib
from types import SimpleNamespace

SETTINGS = '''
# -*- coding: utf-8 -*-
"""
    { Settings }
"""

import pathlib

# Base Directory
BASE_DIR = pathlib.Path(__file__).parents[1]
'''

CONFIG = '''
# -*- coding: utf-8 -*-
"""
    { Config }
"""

from . import settings
'''


def create_base():
    import __main__

    root_dir = pathlib.Path(__main__.__file__).parent
    install_helper = SimpleNamespace()

    install_helper.config_dir = root_dir / "config"
    install_helper.config_file = install_helper.config_dir / "__init__.py"
    install_helper.settings_file = install_helper.config_dir / "settings.py"

    install_helper.config_dir.mkdir(exist_ok=True)

    if not install_helper.config_file.exists():
        with open(install_helper.config_file, "w", encoding="utf8") as file:
            file.write(CONFIG)

    if not install_helper.settings_file.exists():
        with open(install_helper.settings_file, "w", encoding="utf8") as file:
            file.write(SETTINGS)
