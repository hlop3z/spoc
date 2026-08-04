"""
DEPENDENCIES = []

NAME = "auth.models"

def initialize():
    print(f"Initializing {NAME}")
    return True


def teardown():
    print(f"Tearing down {NAME}")
    return True
"""

# Imported objects register where they are defined, not here.
from .models import UserAccount  # noqa: F401
