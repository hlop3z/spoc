"""
The configuration adapter: the only place the kernel reads a file.

``spoc.toml`` is the one configuration file the kernel reads — a project's
``settings.py``, or anything else under its config directory, belongs to the project and
is never imported here. Absent keys fall back to :data:`SPOC_DEFAULTS`, and an absent file
loads as all defaults with a warning naming where it was expected.

The kernel claims exactly one top-level table: ``[spoc]``. Every other top-level table
in the file is application-owned — delivered back as parsed data, never interpreted,
validated, or acted on here. The single claimed table is a stated contract: the kernel
will never claim a second one, so an application's table can never collide with a
kernel one.

Validation is a few explicit checks, not a schema engine. The ``[spoc]`` table is a
closed set of the five keys in :data:`_SPOC_TYPES`, written by the project owner, so a
general-purpose recursive validator was more machinery than the contract it enforced;
see the build-vs-adopt ADR in ``DECISIONS.md``. Closed means enforced: a key outside
that set is a typo, and a typo that merged silently would boot the project on defaults
it never asked for. Parsing stays with stdlib ``tomllib``, which is the adopted standard
for the part that genuinely is standard-format parsing.
"""

from __future__ import annotations

import logging
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any, Final

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

DEFAULT_MODE: Final[str] = "development"

#: The default mode set: each mode maps to its cascade, most specific first.
#: Projects extend or override it per mode under ``[spoc.modes]`` — declared
#: entries merge over these, so adding a mode never means restating the triple.
DEFAULT_MODES: Final[dict[str, list[str]]] = {
    "production": ["production"],
    "staging": ["staging", "production"],
    "development": ["development", "staging", "production"],
}

#: Defaults for the ``[spoc]`` table — any key absent from spoc.toml.
SPOC_DEFAULTS: Final[dict[str, Any]] = {
    "mode": DEFAULT_MODE,
    "debug": False,
    "apps": {},
    "plugins": {},
    "modes": DEFAULT_MODES,
}

#: The closed key set and the type each must hold when present.
_SPOC_TYPES: Final[dict[str, type]] = {
    "mode": str,
    "debug": bool,
    "apps": dict,
    "plugins": dict,
    "modes": dict,
}


def read_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file, or return an empty mapping if it does not exist.

    A file that exists but cannot be read is a configuration failure like any
    other — it never escapes as a bare filesystem error.
    """
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as e:
        raise ConfigurationError(f"Invalid TOML format in {path}: {e!s}") from e
    except OSError as e:  # PermissionError, IsADirectoryError, and the rest
        raise ConfigurationError(f"Cannot read {path}: {e!s}") from e


def validate_spoc_config(config: dict[str, Any]) -> None:
    """Check the ``[spoc]`` table against its closed key set and value types."""
    if "spoc" not in config:
        return
    table = config["spoc"]
    if not isinstance(table, dict):
        raise ConfigurationError(
            "Invalid SPOC configuration: Expected dictionary for 'spoc', "
            f"got {type(table).__name__}"
        )
    valid = ", ".join(_SPOC_TYPES)
    errors = [
        f"Unknown key 'spoc.{key}'. Valid keys: {valid}"
        for key in table
        if key not in _SPOC_TYPES
    ]
    errors += [
        f"Invalid type for 'spoc.{key}': expected {expected.__name__}, "
        f"got {type(table[key]).__name__}"
        for key, expected in _SPOC_TYPES.items()
        if key in table and not isinstance(table[key], expected)
    ]
    # One level deeper: apps, plugins, and modes group name lists. A bare string
    # here is iterable too, and would boot as one app per character — refuse it.
    for key in ("apps", "plugins", "modes"):
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


def load_spoc_toml(base_dir: Path, echo: bool = False) -> dict[str, Any]:
    """Load and validate ``spoc.toml``, filling absent keys from the defaults.

    The returned mapping holds the merged ``spoc`` table plus every
    application-owned top-level table, as parsed. The defaults and the
    application tables are deep-copied into every load. They are (or join)
    module-level structures holding nested dicts and lists; handing them out
    by reference would let one project's configuration be mutated into the
    next one's.
    """
    search_paths = [base_dir / "config" / "spoc.toml", base_dir / "spoc.toml"]

    for path in search_paths:
        if path.exists():
            config = read_toml(path)
            validate_spoc_config(config)
            declared = config.get("spoc", {})
            merged = {**deepcopy(SPOC_DEFAULTS), **deepcopy(declared)}
            # Declared modes extend the default set per mode rather than
            # replacing it, so adding `test` never forces restating the triple.
            merged["modes"] = {
                **deepcopy(DEFAULT_MODES),
                **deepcopy(declared.get("modes", {})),
            }
            # Application-owned tables ride along untouched: parsed, never
            # validated, never silently dropped.
            tables = {k: deepcopy(v) for k, v in config.items() if k != "spoc"}
            return {**tables, "spoc": merged}

    if echo:
        logger.warning(
            "No spoc.toml found at %s or %s. Using default configuration "
            "(development mode, no apps, no plugins).",
            search_paths[0],
            search_paths[1],
        )
    return {"spoc": deepcopy(SPOC_DEFAULTS)}


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
