# -*- coding: utf-8 -*-

"""
Tool for handling TOML files
"""

import tomllib
from pathlib import Path
from typing import Any, Dict


class TOML:
    """A wrapper class for managing TOML files."""

    def __init__(self, file: Path):
        """
        Initialize the TOML manager with the given file path.
        """
        self.file = file

    def read(self) -> Dict[str, Any]:
        """
        Read and parse the TOML file.
        """
        with open(self.file, "rb") as active_file:
            parsed_toml = tomllib.load(active_file)
        return parsed_toml
