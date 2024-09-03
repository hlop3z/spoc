"""Test - Library"""

import asyncio
import functools
import pathlib
import sys
import pytest

pytest_plugins = ("pytest_asyncio",)


def add_to_sys_path(depth: int, sub_path: str = None):
    """Add a directory to sys.path by navigating up a specified number of levels and optionally appending a subdirectory.

    Args:
        depth (int): The number of levels to move up from the current file's directory.
        sub_path (str, optional): An additional subdirectory to append to the resulting path. Defaults to None.
    """
    base_path = pathlib.Path(__file__).parents[depth]
    target_path = base_path / sub_path if sub_path else base_path
    sys.path.append(str(target_path))


@pytest.fixture(scope="session")
def spoc():
    # Add current directory to sys.path
    add_to_sys_path(0)

    # Import spoc project module after sys.path is updated
    import spoc as project

    return project


@pytest.fixture(scope="session")
def app():
    from framework import MyFramework

    return MyFramework()


def test_settings_debug(spoc):
    assert spoc.settings.DEBUG is True


def test_settings_mode(spoc):
    assert spoc.settings.MODE == "development"


def test_settings_env(spoc):
    assert dict(spoc.settings.ENV) == {"key": "value", "child": {"arg": "other_value"}}


def test_settings_spoc(spoc):
    assert dict(spoc.settings.SPOC) == {
        "mode": "development",
        "debug": True,
        "apps": {"production": [], "development": [], "staging": []},
        "plugins": {
            "middleware": ["demo.middleware.MyClass"],
            "on_startup": [],
            "on_shutdown": [],
        },
    }


def test_framework_components(spoc, app):
    assert list(app.components.__dict__.keys()) == ["commands", "models", "views"]


def test_framework_plugins(spoc, app):
    assert list(app.plugins.keys()) == ["on_startup", "middleware", "on_shutdown"]
