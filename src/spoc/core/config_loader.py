"""
Configuration Loading Utilities

This module provides functions for discovering and loading configuration files
from various common locations in a SPOC project.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from .exceptions import ConfigurationError
from .logging_utils import LazyLogger
from .toml_core import TOML, validate_spoc_config

lazy_logger = LazyLogger(__name__)


def _import_module_from_path(module_path: Path, module_name: str) -> ModuleType:
    """
    Dynamically import a module from a file path.

    Args:
        module_path: Path to the Python module file
        module_name: Name to give the imported module

    Returns:
        The imported module object

    Raises:
        ConfigurationError: If the module cannot be imported
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if not spec or not spec.loader:
            raise ConfigurationError(f"Could not load module spec from {module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        raise ConfigurationError(f"Failed to import {module_path}: {str(e)}") from e


def discover_config_module(
    base_dir: Path, possible_names: set[str] | None = None
) -> tuple[Path | None, str | None]:
    """
    Discover configuration module in standard locations.

    Args:
        base_dir: The project base directory
        possible_names: Optional set of possible module names to check

    Returns:
        Tuple of (config_path, module_name) or (None, None) if not found
    """
    possible_names = possible_names or {"settings", "config", "configuration"}

    # Search for a config module in various locations
    search_paths = [
        base_dir / "config",
        base_dir / "conf",
        base_dir,
    ]

    for path in search_paths:
        if not path.exists() or not path.is_dir():
            continue

        # Try as a Python module (directory with __init__.py)
        for name in possible_names:
            module_dir = path / name
            if module_dir.is_dir() and (module_dir / "__init__.py").exists():
                return module_dir / "__init__.py", name

        # Try as a Python file
        for name in possible_names:
            module_file = path / f"{name}.py"
            if module_file.exists():
                return module_file, name

    return None, None


def load_configuration(base_dir: Path) -> ModuleType:
    """
    Load configuration from various possible locations.

    The function searches for configuration files in standard locations and imports
    the first one it finds. It checks for Python modules named 'config', 'settings',
    or 'configuration' in the following locations:
    - {base_dir}/config/
    - {base_dir}/conf/
    - {base_dir}/

    Args:
        base_dir: The project base directory

    Returns:
        The loaded configuration module

    Raises:
        ConfigurationError: If no configuration can be found
    """
    config_path, module_name = discover_config_module(base_dir)

    if not config_path or not module_name:
        raise ConfigurationError(
            "Could not find configuration module. Expected to find 'settings.py', "
            "'config.py', or 'configuration.py' in config/, conf/, or project root."
        )

    # Import the configuration module
    return _import_module_from_path(config_path, module_name)


def load_spoc_toml(base_dir: Path) -> dict[str, Any]:
    """
    Load and validate the SPOC TOML configuration.

    Args:
        base_dir: The project base directory

    Returns:
        The validated SPOC configuration dictionary

    Raises:
        ConfigurationError: If the TOML file is invalid or cannot be found
    """
    # Try standard locations for spoc.toml
    search_paths = [
        base_dir / "config" / "spoc.toml",
        base_dir / "spoc.toml",
    ]

    for path in search_paths:
        if path.exists():
            config = TOML(path).read()
            validate_spoc_config(config)
            return config

    # If no config found, return a minimal valid structure but log a warning
    lazy_logger.warning(
        "No spoc.toml configuration found in standard locations. "
        "Using default minimal configuration. This may cause unexpected behavior.",
    )
    return {"spoc": {"mode": "development", "debug": False, "apps": {}, "plugins": {}}}


def load_environment(
    base_dir: Path, mode: str, env_dir: Path | None = None
) -> dict[str, Any]:
    """
    Load environment-specific configuration from TOML files.

    Args:
        base_dir: The project base directory
        mode: The current application mode (e.g., "development", "production")
        env_dir: Optional custom environment directory path

    Returns:
        Dictionary containing environment variables for the specified mode
    """
    # Determine the environment directory
    if not env_dir:
        env_dir = base_dir / "config" / ".env"
        if not env_dir.exists():
            env_dir = base_dir / ".env"
            if not env_dir.exists():
                lazy_logger.warning(
                    "No .env directory found at %s/config/.env or %s/.env. "
                    "Using empty environment configuration.",
                    base_dir,
                    base_dir,
                )
                return {}

    # Try to load mode-specific environment file
    env_file = env_dir / f"{mode}.toml"
    if env_file.exists():
        return dict(TOML(env_file).read().get("env", {}))

    # Fall back to default environment if mode-specific one doesn't exist
    default_env = env_dir / "default.toml"
    if default_env.exists():
        lazy_logger.warning(
            "No environment configuration found for mode '%s'. "
            "Falling back to default configuration.",
            mode,
        )
        return dict(TOML(default_env).read().get("env", {}))

    lazy_logger.warning(
        "No environment configuration files found for mode '%s' or default. "
        "Using empty environment configuration.",
        mode,
    )
    return {}
