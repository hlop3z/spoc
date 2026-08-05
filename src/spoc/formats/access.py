"""
Addressing into the representation: two standards, split by failure semantics.

:func:`pointer` is RFC 6901. It names exactly one value or raises, and the failure says which
segment stopped resolving — the same per-segment precision the component registry promises.
Use it for configuration, where absence is a defect.

:func:`query` is RFC 9535. It returns a list that may legitimately be empty, because a filter
matching nothing is an answer rather than an error. Use it for datasets.

Neither may be relaxed into the other. That is the whole reason there are two.

**On strict conformance.** ``python-jsonpath`` is a deliberate superset of RFC 9535 — it adds
a keys selector, unions, intersections, a pseudo-root, and a filter context, none of which are
in the standard. Its *conformant* behavior is correct out of the box, including the subtlety
that a bare relative query in a filter is an existence test rather than a truthiness test. What
the default environment will not do is *reject* the extensions, so a query using one would
quietly work here and fail against any other RFC 9535 engine.

:data:`_EXTENSION_TOKENS` therefore rebinds each extension to a sentinel that cannot occur in a
source string. Blanking them to ``""`` looks equivalent and is not: an empty keys-selector token
makes the lexer misparse conformant filters, silently returning the wrong nodes. The sentinel
keeps the lexer intact while making every extension unreachable.
"""

from __future__ import annotations

from functools import cache
from typing import Any, Final

from .errors import MissingDependencyError, PointerResolutionError

#: A character that cannot appear in a query string, used to make a token unmatchable.
#: Not ``""`` — see the module docstring.
_SENTINEL: Final[str] = "\x00"

#: Every ``python-jsonpath`` extension that RFC 9535 does not define.
_EXTENSION_TOKENS: Final[tuple[str, ...]] = (
    "key_token",
    "keys_selector_token",
    "keys_filter_token",
    "union_token",
    "intersection_token",
    "pseudo_root_token",
    "filter_context_token",
)

#: Distinguishes "resolved to null" from "did not resolve" — a contract of the spec.
_MISSING: Final[object] = object()


def _import() -> Any:
    try:
        import jsonpath
    except ImportError as exc:
        raise MissingDependencyError("address values", "query") from exc
    return jsonpath


@cache
def _strict_env() -> Any:
    """The RFC 9535 environment, built once: conformant syntax only, extensions off."""
    jsonpath = _import()
    strict = type(
        "Rfc9535Environment",
        (jsonpath.JSONPathEnvironment,),
        dict.fromkeys(_EXTENSION_TOKENS, _SENTINEL),
    )
    return strict()


@cache
def _pointer_class() -> Any:
    return _import().JSONPointer


def pointer(value: Any, reference: str) -> Any:
    """Resolve an RFC 6901 pointer to exactly one value, or raise naming the segment."""
    cls = _pointer_class()
    parsed = cls(reference)

    resolved = parsed.resolve(value, default=_MISSING)
    if resolved is not _MISSING:
        return resolved

    # Walk prefixes to name the first segment that stopped resolving, rather than
    # reporting a blanket absence for the whole pointer.
    for depth, segment in enumerate(parsed.parts, start=1):
        prefix = cls.from_parts(parsed.parts[:depth])
        if prefix.resolve(value, default=_MISSING) is _MISSING:
            raise PointerResolutionError(reference, segment)
    raise PointerResolutionError(reference, reference)


def query(value: Any, expression: str) -> list[Any]:
    """Apply an RFC 9535 query, returning every match — possibly none."""
    return _strict_env().findall(expression, value)
