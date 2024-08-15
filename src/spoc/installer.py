# -*- coding: utf-8 -*-
"""
File Templates
"""

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

# Installed Apps
INSTALLED_APPS = []
'''.strip()

CONFIG_TEXT = '''
# -*- coding: utf-8 -*-
"""
{ Config }
"""
'''.strip()


SPOC_TEXT = """
[spoc]
# options: production, development, staging
mode = "development"

# Modes
[spoc.apps]
production = []
development = []
staging = []

# Extras
[spoc.extras]
""".strip()


ENV_TEXT = """
[env] # Environment Settings
""".strip()


def start_project():
    """Create Core Files"""

    # import __main__

    # root_dir = pathlib.Path(__main__.__file__).parent
    root_dir = pathlib.Path.cwd()

    path = SimpleNamespace()

    path.config_dir = root_dir / "config"
    path.config_file = path.config_dir / "__init__.py"
    path.settings_file = path.config_dir / "settings.py"
    path.spoc_file = path.config_dir / "spoc.toml"

    # Create Folder
    path.config_dir.mkdir(exist_ok=True)

    # Environment Folder
    env_types = ["production", "development", "staging"]
    env_path = path.config_dir / ".env"
    env_path.mkdir(exist_ok=True)

    # Create Files
    if not path.config_file.exists():
        with open(path.config_file, "w", encoding="utf-8") as file:
            file.write(CONFIG_TEXT)

    if not path.settings_file.exists():
        with open(path.settings_file, "w", encoding="utf-8") as file:
            file.write(SETTINGS_TEXT)

    if not path.spoc_file.exists():
        with open(path.spoc_file, "w", encoding="utf-8") as file:
            file.write(SPOC_TEXT)

    # Environment Create Files
    for env in env_types:
        current_path = env_path / f"{env}.toml"
        if not current_path.exists():
            with open(current_path, "w", encoding="utf-8") as file:
                file.write(ENV_TEXT)
