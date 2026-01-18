"""
Settings
"""

# Standard Library
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent


# Installed Apps
INSTALLED_APPS: list = ["demo"]

# Extra Methods
PLUGINS: dict = {
    "middleware": ["demo.extras.middleware"],
    "hooks": ["demo.extras.hook"],
}
