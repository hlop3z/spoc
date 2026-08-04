"""The entire framework definition: one declaration, two decorators."""

import spoc

framework = spoc.Framework("models", spoc.KindSpec("views", depends_on=("models",)))

model = framework.kind("models")
view = framework.kind("views")
