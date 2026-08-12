"""Composition root for the type-checker conformance fixture.

Deliberately minimal: a stub replaces this module wholesale for type checking,
so it holds the framework and its kind handles and nothing else.
"""

import spoc

framework = spoc.Framework(
    spoc.KindSpec("models", required=False),
    spoc.KindSpec("views", depends_on=("models",), required=False),
    spoc.KindSpec("resources", required=False),
)
model = framework.kind("models")
view = framework.kind("views")
