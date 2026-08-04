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

from .models import UserAccount  # noqa: F401 -- imported objects register where defined, not here
