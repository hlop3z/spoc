"""The entire framework definition: one declaration, two decorators."""

import spoc

# Plugin groups in spoc.toml name declared kinds; required=False means no app
# has to provide a module for them — only configuration populates them.
framework = spoc.Framework(
    "models",
    spoc.KindSpec("views", depends_on=("models",)),
    spoc.KindSpec("middleware", required=False),
    spoc.KindSpec("hooks", required=False),
)

model = framework.kind("models")
view = framework.kind("views")
