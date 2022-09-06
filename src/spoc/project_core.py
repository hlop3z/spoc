"""[ Collect & Inject ]
    Project (Module)
"""


try:
    import project

except ImportError as exception:
    raise ValueError("Missing { ./project/__init__.py } module.") from exception

if not hasattr(project, "settings"):
    raise ValueError("Missing { ./project/settings.py } module.")

if not hasattr(project.settings, "BASE_DIR"):
    raise ValueError(
        """Missing { pathlib.Path(__file__).parents[1] } in file { ./project/settings.py }."""
    )

PROJECT = project
SETTINGS = project.settings
BASE_DIR = project.settings.BASE_DIR
