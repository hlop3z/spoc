import toml

TOML_SETUP = """
[spoc]
name = "my-project"
version = "0.1.0"

[spoc.config]
mode = "development" # development, production, staging 
docs = "mydocs.md"

[spoc.apps]
production = []
development = []
staging = []

[spoc.graphql]
generates = "graphql"
items_per_page = 50
max_depth = 4

[spoc.api]
allowed_hosts = []
middleware = []
extensions = []
permissions = []
on_startup = []
on_shutdown = []
""".strip()


class TOML:
    file = "spoc.toml"
    setup = TOML_SETUP

    @classmethod
    def read(cls):
        with open(cls.file, "r", encoding="utf-8") as found_file:
            toml_string = found_file.read()
            parsed_toml = toml.loads(toml_string)
        return parsed_toml

    @classmethod
    def init(cls):
        with open(cls.file, "w", encoding="utf-8") as file:
            file.write(cls.setup)
