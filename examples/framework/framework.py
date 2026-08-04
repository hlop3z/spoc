"""The entire framework definition: one declaration, two decorators."""

import spoc

framework = spoc.Framework("models", "views", dependencies={"views": ["models"]})

model = framework.kind("models")
view = framework.kind("views")
