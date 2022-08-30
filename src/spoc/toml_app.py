"""
    Tool for TOML (before tomlib gets implemented)
"""

import toml

TOML_SETUP = """
[spoc]
name = "my-project"
version = "0.1.0"

[spoc.config]
mode = "development" # development, production, staging, custom

[spoc.apps]
production = []
development = []
staging = []
""".strip()


class TOML:
    """TOML Wrapper"""

    file = "spoc.toml"
    setup = TOML_SETUP

    @classmethod
    def read(cls):
        """Read"""
        with open(cls.file, "r", encoding="utf-8") as found_file:
            toml_string = found_file.read()
            parsed_toml = toml.loads(toml_string)
        return parsed_toml

    @classmethod
    def init(cls):
        """Initialize"""
        with open(cls.file, "w", encoding="utf-8") as file:
            file.write(cls.setup)
