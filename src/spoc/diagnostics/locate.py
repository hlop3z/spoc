"""
Locating a project's framework declaration.

The scaffold emits the convention — a top-level ``framework.py`` exposing
``framework`` — so the default reference is ``framework:framework``. Projects
shaped differently state ``module.path:attribute`` explicitly. The caller is
responsible for making the project root importable (the operations do it
inside an isolation scope).
"""

from __future__ import annotations

import importlib

from ..framework import Framework

__all__ = ["DEFAULT_FRAMEWORK_REF", "LocateError", "locate_framework"]

#: What ``spoc init`` emits: module ``framework``, attribute ``framework``.
DEFAULT_FRAMEWORK_REF = "framework:framework"


class LocateError(RuntimeError):
    """The framework declaration could not be found — says where it looked
    and how to override, so the failure is actionable."""


def _fail(ref: str, problem: str) -> LocateError:
    return LocateError(
        f"Could not locate the framework declaration: {problem}. "
        f"Looked for {ref!r} (module:attribute). If the project is shaped "
        f"differently, state it explicitly with --framework module.path:attribute"
    )


def locate_framework(ref: str = DEFAULT_FRAMEWORK_REF) -> Framework:
    """Import `ref` (``module:attr``) and return the :class:`Framework` it names."""
    module_path, sep, attribute = ref.partition(":")
    if not sep or not module_path or not attribute:
        raise _fail(ref, f"{ref!r} is not of the form module:attribute")
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise _fail(
            ref, f"module {module_path!r} could not be imported ({exc})"
        ) from exc
    try:
        framework = getattr(module, attribute)
    except AttributeError as exc:
        raise _fail(
            ref, f"module {module_path!r} has no attribute {attribute!r}"
        ) from exc
    if not isinstance(framework, Framework):
        raise _fail(
            ref,
            f"{module_path}:{attribute} is {type(framework).__name__}, not a Framework",
        )
    return framework
