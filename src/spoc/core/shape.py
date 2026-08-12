"""
The shape of a registered object: constructible, callable, or value.

Shape is the one property of a component the kernel classifies at runtime, and
it is deliberately coarse. Which *members* an object provides is a static
question, answered where the contract is visible; classifying it here too would
put a validation engine in the kernel. Three shapes are all typed access needs,
because ``type[T]`` versus ``T`` is the only distinction the type system forces.

This module exists so there is exactly one classifier. Typed access reports a
shape in an error, a generated stub records one per identifier, and the registry
projection publishes one to consumers outside the process — three readers of one
fact, which is one classifier or it is drift.
"""

from __future__ import annotations

from typing import Final, Literal

#: The three shapes a registered object can have, as the projection publishes
#: them. Language-neutral by intent: "constructible" says what a consumer may
#: do with the object, where "class" would name a Python spelling and mean
#: nothing to a reader in another language.
Shape = Literal["constructible", "callable", "value"]

#: How each shape reads inside a sentence. Typed access's refusals are prose —
#: "Component 'x' is a callable, but ..." — so the article belongs to the
#: rendering, never to the token.
SHAPE_PROSE: Final[dict[Shape, str]] = {
    "constructible": "a constructible object",
    "callable": "a callable",
    "value": "a value",
}


def shape_of(obj: object) -> Shape:
    """Classify a registered object.

    The order is not incidental and cannot be reversed: a class is callable
    too, so constructibility has to be tested first or every class would
    classify as a callable.
    """
    if isinstance(obj, type):
        return "constructible"
    if callable(obj):
        return "callable"
    return "value"


def shape_prose(obj: object) -> str:
    """Name an object's shape as it reads in an error message."""
    return SHAPE_PROSE[shape_of(obj)]
