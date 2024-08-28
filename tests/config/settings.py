# -*- coding: utf-8 -*-
"""
{ Settings }
"""

import pathlib

# Base Directory
BASE_DIR = pathlib.Path(__file__).parents[1]

# Installed Apps
INSTALLED_APPS = ["demo"]

# Extra Methods
PLUGINS = {
    "on_startup": ["demo.middleware.on_event"],
}
