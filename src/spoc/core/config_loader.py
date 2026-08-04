"""
Configuration Loading Utilities

This module loads the kernel's declarative configuration: ``spoc.toml`` and
the per-mode environment TOML files. These are the only configuration files
the kernel reads — a user's ``settings.py`` (or any other module) is theirs
alone and is never imported by SPOC.
"""

import logging
from pathlib import Path
from typing import Any

from .toml_core import TOML, validate_spoc_config

logger = logging.getLogger(__name__)

DEFAULT_MODE = "development"

#: Defaults for the ``[spoc]`` table — any key absent from spoc.toml.
SPOC_DEFAULTS: dict[str, Any] = {
    "mode": DEFAULT_MODE,
    "debug": False,
    "apps": {},
    "plugins": {},
}


def load_spoc_toml(base_dir: Path) -> dict[str, Any]:
    """
    Load and validate the SPOC TOML configuration.

    Absent keys fall back to :data:`SPOC_DEFAULTS`; a missing file loads as
    all defaults with a warning naming the expected location.

    Args:
        base_dir: The project base directory

    Returns:
        The validated SPOC configuration dictionary

    Raises:
        ConfigurationError: If the TOML file is invalid
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
            return {"spoc": {**SPOC_DEFAULTS, **config.get("spoc", {})}}

    # If no config found, return the defaults but log a warning
    logger.warning(
        "No spoc.toml found at %s or %s. Using default configuration "
        "(development mode, no apps, no plugins).",
        search_paths[0],
        search_paths[1],
    )
    return {"spoc": dict(SPOC_DEFAULTS)}


def load_environment(
    base_dir: Path, mode: str, env_dir: Path | None = None, echo: bool = False
) -> dict[str, Any]:
    """
    Load environment-specific configuration from TOML files.

    Args:
        base_dir: The project base directory
        mode: The current application mode (e.g., "development", "production")
        env_dir: Optional custom environment directory path
        echo: Whether to log warnings about missing configuration files

    Returns:
        Dictionary containing environment variables for the specified mode.
        Falls back to ``default.toml`` when no mode-specific file exists.
    """
    # Determine the environment directory
    if not env_dir:
        env_dir = base_dir / "config" / ".env"
        if not env_dir.exists():
            env_dir = base_dir / ".env"

    if not env_dir.exists():
        if echo:
            logger.warning(
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
        if echo:
            logger.warning(
                "No environment configuration found for mode '%s'. "
                "Falling back to default configuration.",
                mode,
            )
        return dict(TOML(default_env).read().get("env", {}))

    if echo:
        logger.warning(
            "No environment configuration files found for mode '%s' or default. "
            "Using empty environment configuration.",
            mode,
        )
    return {}
