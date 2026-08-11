"""The entire framework definition: one declaration, three decorators."""

import spoc


# The vocabulary's resource recipe: the kind's hooks open every declared
# resource before any view runs and close them all on the way out. The hook
# receives each app's declared resource objects, in canonical order.
def _open(resources):
    for resource_obj in resources:
        resource_obj.open()


def _close(resources):
    for resource_obj in resources:
        resource_obj.close()


# Plugin groups in spoc.toml name declared kinds; required=False means no app
# has to provide a module for them — only configuration populates them, or
# (for resources) only the apps that have one declare one.
framework = spoc.Framework(
    "models",
    spoc.KindSpec("views", depends_on=("models",)),
    spoc.KindSpec("resources", required=False, on_startup=_open, on_shutdown=_close),
    spoc.KindSpec("middleware", required=False),
    spoc.KindSpec("hooks", required=False),
)

model = framework.kind("models")
view = framework.kind("views")
resource = framework.kind("resources")
