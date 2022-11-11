"""
    Tool for TOML (before tomlib gets implemented)
"""

import toml


class TOML:
    """TOML Wrapper"""

    def __init__(self, file=None):
        """Initialize TOML-Manager"""

        self.file = file

        if not file:
            raise ValueError("Please Set a <Path> for the <TOML> file.")

    def read(self):
        """Read"""

        with open(self.file, "r", encoding="utf-8") as active_file:
            toml_string = active_file.read()
            parsed_toml = toml.loads(toml_string)
        return parsed_toml
