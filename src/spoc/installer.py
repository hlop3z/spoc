# -*- coding: utf-8 -*-
"""
File Templates
"""

import pathlib
from types import SimpleNamespace

CONFIG_TEXT = '''
# -*- coding: utf-8 -*-
"""
Config
"""
'''.strip()

SETTINGS_TEXT = '''
# -*- coding: utf-8 -*-
"""
Settings
"""

import pathlib

# Base Directory
BASE_DIR = pathlib.Path(__file__).parents[1]

# Installed Apps
INSTALLED_APPS: list  = []

# Extra Methods
PLUGINS: dict = {}
'''.strip()


SPOC_TEXT = """
# Application Configuration
[spoc]
mode = "development" # options: development, staging, production
debug = true

# Installed Apps by Mode
[spoc.apps]
production = []
development = []
staging = []

# Additional Components
[spoc.plugins] # (Plugins and Hooks)
""".strip()


ENV_TEXT = """
[env] # Environment Settings
""".strip()


def start_project(
    settings_text: str = SETTINGS_TEXT,
    spoc_text: str = SPOC_TEXT,
    env_text: str = ENV_TEXT,
):
    """
    Creates the core configuration files and directories for a project.

    This function sets up the initial directory structure and creates the necessary
    configuration files for a new project, including `settings.py`, `spoc.toml`,
    and environment-specific configuration files.

    Args:
        settings_text (str): The text content for the `settings.py` file.
        spoc_text (str): The text content for the `spoc.toml` file.
        env_text (str): The text content for environment-specific `.toml` files
                        (e.g., `production.toml`, `development.toml`, `staging.toml`).
    """
    config_text: str = CONFIG_TEXT

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
            file.write(config_text)

    if not path.settings_file.exists():
        with open(path.settings_file, "w", encoding="utf-8") as file:
            file.write(settings_text)

    if not path.spoc_file.exists():
        with open(path.spoc_file, "w", encoding="utf-8") as file:
            file.write(spoc_text)

    # Environment Create Files
    for env in env_types:
        current_path = env_path / f"{env}.toml"
        if not current_path.exists():
            with open(current_path, "w", encoding="utf-8") as file:
                file.write(env_text)
