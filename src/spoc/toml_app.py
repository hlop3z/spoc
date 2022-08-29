import toml

TOML_SETUP = """
[spoc]
name = "my-project"
version = "0.1.0"

[spoc.config]
# development, production, staging
mode = "development" 
docs = "mydocs.md"

[spoc.apps]
production = []
development = []
staging = []

[spoc.graphql]
items_per_page = 50
max_depth = 4
generates = "graphql"

[spoc.fastapi]
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
    def read(cls, found_file=None):
        found_file = found_file or cls.file
        with open(found_file, "r", encoding="utf-8") as found_file:
            toml_string = found_file.read()
            parsed_toml = toml.loads(toml_string)
        return parsed_toml

    @classmethod
    def write(cls, parsed_toml):
        with open(cls.file, "w", encoding="utf-8") as file:
            toml.dump(parsed_toml, file)

    @classmethod
    def init(cls):
        with open(cls.file, "w", encoding="utf-8") as file:
            file.write(cls.setup)
