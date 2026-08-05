"""
The configuration adapter: the only place the kernel reads a file.

``spoc.toml`` is the one configuration file the kernel reads — a project's
``settings.py``, or anything else under its config directory, belongs to the project and
is never imported here. Absent keys fall back to :data:`SPOC_DEFAULTS`, and an absent file
loads as all defaults with a warning naming where it was expected.

Validation is four explicit checks, not a schema engine. The ``[spoc]`` table is a closed
set of four keys written by the project owner, so a general-purpose recursive validator
was more machinery than the contract it enforced; see the build-vs-adopt ADR in
``DECISIONS.md``. Parsing stays with stdlib ``tomllib``, which is the adopted standard for
the part that genuinely is standard-format parsing.
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any, Final

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

DEFAULT_MODE: Final[str] = "development"

#: Defaults for the ``[spoc]`` table — any key absent from spoc.toml.
SPOC_DEFAULTS: Final[dict[str, Any]] = {
    "mode": DEFAULT_MODE,
    "debug": False,
    "apps": {},
    "plugins": {},
}

#: The closed key set and the type each must hold when present.
_SPOC_TYPES: Final[dict[str, type]] = {
    "mode": str,
    "debug": bool,
    "apps": dict,
    "plugins": dict,
}


def read_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file, or return an empty mapping if it does not exist."""
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as e:
        raise ConfigurationError(f"Invalid TOML format in {path}: {e!s}") from e


def validate_spoc_config(config: dict[str, Any]) -> None:
    """Check the ``[spoc]`` table's four keys, ignoring any that are absent."""
    if "spoc" not in config:
        return
    table = config["spoc"]
    if not isinstance(table, dict):
        raise ConfigurationError(
            "Invalid SPOC configuration: Expected dictionary for 'spoc', "
            f"got {type(table).__name__}"
        )
    errors = [
        f"Invalid type for 'spoc.{key}': expected {expected.__name__}, "
        f"got {type(table[key]).__name__}"
        for key, expected in _SPOC_TYPES.items()
        if key in table and not isinstance(table[key], expected)
    ]
    # One level deeper: apps and plugins group name lists. A bare string here is
    # iterable too, and would boot as one app per character — refuse it loudly.
    for key in ("apps", "plugins"):
        if not isinstance(table.get(key), dict):
            continue
        errors.extend(
            f"Invalid type for 'spoc.{key}.{group}': expected list of str, "
            f"got {type(names).__name__}"
            for group, names in table[key].items()
            if not (isinstance(names, list) and all(isinstance(n, str) for n in names))
        )
    if errors:
        raise ConfigurationError("Invalid SPOC configuration: " + "; ".join(errors))


def load_spoc_toml(base_dir: Path) -> dict[str, Any]:
    """Load and validate ``spoc.toml``, filling absent keys from the defaults."""
    search_paths = [base_dir / "config" / "spoc.toml", base_dir / "spoc.toml"]

    for path in search_paths:
        if path.exists():
            config = read_toml(path)
            validate_spoc_config(config)
            return {"spoc": {**SPOC_DEFAULTS, **config.get("spoc", {})}}

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
    """Load the environment table for `mode`, falling back to ``default.toml``."""
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

    env_file = env_dir / f"{mode}.toml"
    if env_file.exists():
        return dict(read_toml(env_file).get("env", {}))

    default_env = env_dir / "default.toml"
    if default_env.exists():
        if echo:
            logger.warning(
                "No environment configuration found for mode '%s'. "
                "Falling back to default configuration.",
                mode,
            )
        return dict(read_toml(default_env).get("env", {}))

    if echo:
        logger.warning(
            "No environment configuration files found for mode '%s' or default. "
            "Using empty environment configuration.",
            mode,
        )
    return {}
