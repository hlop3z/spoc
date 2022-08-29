"""
Project Config
"""

import pathlib

import spoc

# Core
CORE_MODULES = ["types", "graphql"]

# Custom
BASE_DIR = pathlib.Path(__file__).resolve().parents[0]
INSTALLED_APPS = ["app_one", "app_two"]

# Init
App = spoc.Spoc(base_dir=BASE_DIR)

# Load Apps
App.load_apps(plugins=CORE_MODULES, installed_apps=INSTALLED_APPS)

# Test
test = spoc.Spoc()

print(test.keys, end="\n\n")
print(test.schema["types"].keys())
