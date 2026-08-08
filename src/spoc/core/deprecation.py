"""
PEP 702 ``@deprecated`` — the one import site for the deprecation signal.

The release policy requires that withdrawing a public name first produce a runtime
signal a consumer can suppress or escalate, and that a type checker can see. PEP 702
is that standard, so it is adopted rather than reinvented.

It reached the standard library as :func:`warnings.deprecated` in 3.13, and this
package supports 3.12, so the gap is bridged here with a stdlib-only fallback. Taking
``typing_extensions`` — the canonical backport — would put a runtime dependency into a
distribution whose ``dependencies`` list is deliberately empty, which costs more than
the twenty lines below.

On 3.13+ the standard library's own decorator is used unchanged, so the fallback
deletes itself the day this package's floor moves to 3.13.
"""

from __future__ import annotations

import functools
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

_T = TypeVar("_T")


def _fallback_deprecated(
    message: str,
    /,
    *,
    category: type[Warning] | None = DeprecationWarning,
    stacklevel: int = 1,
) -> Callable[[_T], _T]:
    """A minimal PEP 702 ``@deprecated`` for interpreters without the stdlib one.

    Covers what the policy actually requires: the object still works, using it warns
    once per call site with a message naming the element and its replacement, and
    ``__deprecated__`` is set so a type checker or a test can see the mark. Passing
    ``category=None`` marks without warning, as the PEP specifies.
    """

    def decorator(arg: _T) -> _T:
        if isinstance(arg, type):
            original_new = arg.__new__

            def patched_new(cls, *args: Any, **kwargs: Any):
                if category is not None:
                    warnings.warn(message, category=category, stacklevel=stacklevel + 1)
                # object.__new__ rejects extra arguments when __init__ is overridden.
                if original_new is object.__new__:
                    return original_new(cls)
                return original_new(cls, *args, **kwargs)

            arg.__new__ = staticmethod(patched_new)
            arg.__deprecated__ = patched_new.__deprecated__ = message
            return arg

        @functools.wraps(arg)
        def wrapper(*args: Any, **kwargs: Any):
            if category is not None:
                warnings.warn(message, category=category, stacklevel=stacklevel + 1)
            return arg(*args, **kwargs)

        arg.__deprecated__ = wrapper.__deprecated__ = message
        return wrapper

    return decorator


try:  # Python 3.13+
    from warnings import deprecated
except ImportError:  # pragma: no cover - exercised only on 3.12
    deprecated = _fallback_deprecated
