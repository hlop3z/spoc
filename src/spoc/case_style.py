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
from functools import cache
from typing import Callable, Final, Literal, TypeAlias, TypeGuard

# —— Constants & Patterns —— #
_CAMEL_BOUNDARY: Final[re.Pattern] = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
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


@cache
def to_snake_case(s: str, clip_edges: bool = True) -> str:
    """AnyCase → snake_case."""
    words = _split_to_words(s)
    result = "_".join(words)
    return result if clip_edges else f"_{result}_"


@cache
def to_pascal_case(s: str) -> str:
    """snake_case (or any) → PascalCase."""
    return "".join(word.capitalize() for word in _split_to_words(s))


@cache
def to_camel_case(s: str) -> str:
    """snake_case (or any) → camelCase."""
    words = _split_to_words(s)
    return words[0] + "".join(w.capitalize() for w in words[1:]) if words else ""


@cache
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


# —— Self-test block —— #
if __name__ == "__main__":
    examples: list[tuple[str, CaseStyle]] = [
        ("TestString", "pascal"),
        ("TestString", "camel"),
        ("testString", "kebab"),
        ("Test-String", "snake"),
        ("Test--String", "snake"),
        ("__Test__String__", "snake"),
    ]
    for text, mode in examples:
        print(f"{text!r} → ({mode}) {case_style(text, mode)}")
