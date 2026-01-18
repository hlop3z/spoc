"""
Tool for handling TOML files and configuration validation.
"""

import tomllib
from pathlib import Path
from typing import Any, Dict, Mapping, Type, Union

from .exceptions import ConfigurationError

# Type alias for schema definition
SchemaType = Union[Type, Dict[str, Any]]
SchemaDict = Dict[str, SchemaType]


class TOML:
    """A wrapper class for managing TOML files."""

    def __init__(self, file: Path) -> None:
        """
        Initialize the TOML manager with the given file path.

        Args:
            file: Path to the TOML file.
        """
        self.file = file

    def read(self) -> dict[str, Any]:
        """
        Read and parse the TOML file.

        Returns:
            dict containing the parsed TOML content.

        Raises:
            ConfigurationError: If the file cannot be read or parsed.
        """
        try:
            with open(self.file, "rb") as active_file:
                parsed_toml = tomllib.load(active_file)
            return parsed_toml
        except FileNotFoundError:
            return {}
        except tomllib.TOMLDecodeError as e:
            raise ConfigurationError(
                f"Invalid TOML format in {self.file}: {str(e)}"
            ) from e


def validate_config(
    config: dict[str, Any],
    schema: Mapping[str, SchemaType],
    path_prefix: str = "",
) -> tuple[bool, list[str]]:
    """
    Validate a configuration dictionary against a schema.

    Args:
        config: The configuration dictionary to validate.
        schema: A schema dictionary where keys are configuration keys
            and values are either expected types or nested schema dictionaries.
        path_prefix: Current path prefix for nested validation (used internally).

    Returns:
        A tuple containing (is_valid, error_messages).
    """
    errors: list[str] = []

    # Check for required keys and correct types
    for key, expected_type in schema.items():
        # Build the current path
        current_path = f"{path_prefix}{key}" if path_prefix else key

        if key not in config:
            errors.append(f"Missing required key: {current_path}")
            continue

        if isinstance(expected_type, dict):
            # Recursive validation for nested dictionaries
            if not isinstance(config[key], dict):
                errors.append(
                    f"Expected dictionary for '{current_path}', got {type(config[key]).__name__}"
                )
            else:
                # Use dot notation for nested paths
                nested_prefix = f"{current_path}."
                valid, nested_errors = validate_config(
                    config[key], expected_type, nested_prefix
                )
                if not valid:
                    errors.extend(nested_errors)
        else:
            # Type validation for simple values
            if not isinstance(config[key], expected_type):
                errors.append(
                    f"Invalid type for '{current_path}': expected {expected_type.__name__}, "
                    f"got {type(config[key]).__name__}"
                )

    return len(errors) == 0, errors


def validate_spoc_config(config: dict[str, Any]) -> None:
    """
    Validate the SPOC configuration structure.

    Args:
        config: The SPOC configuration dictionary to validate.

    Raises:
        ConfigurationError: If the configuration is invalid.
    """
    schema: SchemaDict = {
        "spoc": {"mode": str, "debug": bool, "apps": dict, "plugins": dict}
    }

    is_valid, errors = validate_config(config, schema)
    if not is_valid:
        error_message = "Invalid SPOC configuration: " + "; ".join(errors)
        raise ConfigurationError(error_message)
