"""
Case style conversion utilities.

This module provides functions to convert strings between different case styles:
- snake_case
- camelCase
- PascalCase
- kebab-case
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Callable, Final, Literal, TypeAlias, TypeGuard

#: Bounded so converting attacker- or user-supplied strings cannot grow the
#: cache without limit. Declaration-time names are far below this.
_CACHE_SIZE: Final[int] = 2048

# —— Constants & Patterns —— #
#: Word boundaries inside a camel/Pascal name. Two rules, both needed:
#: a lower/digit→upper transition (``userAccount`` → ``user|Account``), and
#: the tail of an acronym before a capitalized word (``HTTPServer`` →
#: ``HTTP|Server``). Without the second, acronyms collapse (``httpserver``).
_CAMEL_BOUNDARY: Final[re.Pattern] = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
_SEPARATOR_CHARS: Final[str] = r"[_\-]+"
_CLEAN_EDGE: Final[re.Pattern] = re.compile(rf"^{_SEPARATOR_CHARS}|{_SEPARATOR_CHARS}$")

CaseStyle: TypeAlias = Literal["snake", "camel", "pascal", "kebab"]


def _split_to_words(s: str) -> list[str]:
    """Normalize any case to a list of lowercase words."""
    # 1. Insert separator before camel-pascal boundaries
    s = _CAMEL_BOUNDARY.sub("_", s)
    # 2. Replace hyphens with underscores, collapse multiples
    s = re.sub(_SEPARATOR_CHARS, "_", s)
    # 3. Strip edge separators, lowercase, split
    s = _CLEAN_EDGE.sub("", s).lower()
    return [w for w in s.split("_") if w]


@lru_cache(maxsize=_CACHE_SIZE)
def to_snake_case(s: str, clip_edges: bool = True) -> str:
    """AnyCase → snake_case."""
    words = _split_to_words(s)
    result = "_".join(words)
    return result if clip_edges else f"_{result}_"


@lru_cache(maxsize=_CACHE_SIZE)
def to_pascal_case(s: str) -> str:
    """snake_case (or any) → PascalCase."""
    return "".join(word.capitalize() for word in _split_to_words(s))


@lru_cache(maxsize=_CACHE_SIZE)
def to_camel_case(s: str) -> str:
    """snake_case (or any) → camelCase."""
    words = _split_to_words(s)
    return words[0] + "".join(w.capitalize() for w in words[1:]) if words else ""


@lru_cache(maxsize=_CACHE_SIZE)
def to_kebab_case(s: str) -> str:
    """snake_case (or any) → kebab-case."""
    return "-".join(_split_to_words(s))


def is_valid_case_style(mode: str) -> TypeGuard[CaseStyle]:
    """True if `mode` is one of the supported case styles."""
    return mode in ("snake", "camel", "pascal", "kebab")


def case_style(
    s: str,
    mode: CaseStyle = "snake",
    clip_edges: bool = True,
) -> str:
    """
    Convert string `s` between case styles by normalizing to words first.

    Examples:
        >>> case_style("HelloWorld", "snake")
        "hello_world"
        >>> case_style("hello_world", "pascal")
        "HelloWorld"
        >>> case_style("Hello-World", "kebab")
        "hello-world"
    """
    converters: dict[CaseStyle, Callable[[str], str]] = {
        "snake": lambda x: to_snake_case(x, clip_edges),
        "camel": to_camel_case,
        "pascal": to_pascal_case,
        "kebab": to_kebab_case,
    }

    try:
        return converters[mode](s)
    except KeyError:
        raise ValueError(f"Invalid case style: {mode!r}") from None
