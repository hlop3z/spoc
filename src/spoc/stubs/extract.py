"""
Turning live registered objects into static type references.

The describe pass holds the *objects*, not their source, so extraction reads
``__module__``/``__qualname__`` and :func:`inspect.signature` directly rather
than parsing anything. That is the whole reason this is stdlib work: a source
reader would re-derive what the registry already knows, and would be blind to
components registered from ``[spoc.plugins]``, which exist only once
configuration has resolved.

Two rules govern everything here. **Absence over guessing**: when a type cannot
be named faithfully the reference degrades to ``Any`` and says so, so the count
of degraded entries is reportable instead of a stub quietly lying. And **names
are aliased, never bare**: two apps may each declare a ``Product``, so every
imported name enters the stub under a deterministic alias derived from its
module path. Collisions are then impossible rather than unlikely.
"""

from __future__ import annotations

import inspect
import types
import typing
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Final, Literal

from ..core.shape import shape_of

#: Builtins that need no import and render as their own name.
_BUILTINS: Final[frozenset[type]] = frozenset(
    {bool, bytes, complex, float, int, object, str}
)

#: Generic origins whose rendering is ``origin[arg, ...]`` with the origin's
#: own lowercase builtin spelling.
_BUILTIN_GENERICS: Final[frozenset[type]] = frozenset(
    {dict, frozenset, list, set, tuple}
)


def alias_for(module: str, name: str) -> str:
    """The deterministic local name an imported type takes inside a stub.

    Derived from the full module path, so two apps declaring the same class
    name cannot collide, and the same input always produces the same alias.
    """
    flattened = module.replace(".", "_")
    return f"_{flattened}_{name.replace('.', '_')}"


@dataclass(frozen=True)
class TypeRef:
    """A rendered static type plus whatever must be imported to name it."""

    expression: str
    #: ``(module, top_level_name)`` pairs; the stub imports each under its alias.
    imports: tuple[tuple[str, str], ...] = ()
    degraded: bool = False


@dataclass
class _Render:
    """Mutable accumulator while rendering one annotation tree."""

    imports: set[tuple[str, str]] = field(default_factory=set)
    degraded: bool = False

    def finish(self, expression: str) -> TypeRef:
        return TypeRef(
            expression=expression,
            imports=tuple(sorted(self.imports)),
            degraded=self.degraded,
        )


def _named_type(state: _Render, tp: type) -> str:
    """Render a class by name, recording the import it needs."""
    if tp in _BUILTINS:
        return tp.__name__
    if tp is type(None):
        return "None"
    module = getattr(tp, "__module__", None)
    qualname = getattr(tp, "__qualname__", None)
    if not module or not qualname or "<locals>" in qualname:
        # Locally-defined or introspection-hostile: nothing importable to name.
        state.degraded = True
        return "Any"
    if module == "builtins":
        return qualname
    root = qualname.split(".")[0]
    state.imports.add((module, root))
    return alias_for(module, root) + qualname[len(root) :]


def _render(state: _Render, annotation: Any) -> str:
    """Render one annotation, recursing through the generics we can name."""
    if annotation is inspect.Signature.empty:
        state.degraded = True
        return "Any"
    if annotation is Any:
        return "Any"
    if annotation is None or annotation is type(None):
        return "None"
    if isinstance(annotation, str):
        # An unresolved forward reference. Naming it would require guessing
        # which module it resolves in.
        state.degraded = True
        return "Any"

    origin = typing.get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type):
            return _named_type(state, annotation)
        state.degraded = True
        return "Any"

    args = typing.get_args(annotation)
    if origin is typing.Union or origin is types.UnionType:
        return " | ".join(_render(state, a) for a in args)
    if origin is Literal:
        return f"Literal[{', '.join(repr(a) for a in args)}]"
    if origin in _BUILTIN_GENERICS:
        if not args:
            return origin.__name__
        rendered = ", ".join(_render(state, a) for a in args)
        return f"{origin.__name__}[{rendered}]"
    if origin is Callable or origin is typing.Callable:
        return _render_callable_generic(state, args)

    state.degraded = True
    return "Any"


def _render_callable_generic(state: _Render, args: tuple[Any, ...]) -> str:
    state.imports.add(("collections.abc", "Callable"))
    name = alias_for("collections.abc", "Callable")
    if not args:
        return f"{name}[..., Any]"
    *params, result = args
    rendered_result = _render(state, result)
    if len(params) == 1 and params[0] is Ellipsis:
        return f"{name}[..., {rendered_result}]"
    flat = params[0] if len(params) == 1 and isinstance(params[0], list) else params
    if not isinstance(flat, list | tuple):
        return f"{name}[..., {rendered_result}]"
    rendered_params = ", ".join(_render(state, p) for p in flat)
    return f"{name}[[{rendered_params}], {rendered_result}]"


def _hints_for(func: Any) -> dict[str, Any]:
    """Resolved annotations for a callable, or empty when they cannot resolve.

    ``from __future__ import annotations`` makes every annotation a string, so
    resolution has to be attempted; a module whose names do not resolve yields
    nothing rather than a stub full of quoted guesses.
    """
    try:
        return typing.get_type_hints(func)
    except Exception:  # unresolvable forward refs, exotic namespaces
        return {}


def reference_for(obj: object) -> TypeRef:
    """The static type a consumer obtains when reading this object.

    A class yields ``type[X]`` — the registry hands back the class itself, not
    an instance of it. A value yields its own type. A callable yields its
    signature, as precisely as its annotations allow.
    """
    kind = shape_of(obj)
    if kind == "constructible":
        state = _Render()
        rendered = _named_type(state, typing.cast("type", obj))
        if state.degraded:
            return state.finish("Any")
        return state.finish(f"type[{rendered}]")
    if kind == "value":
        state = _Render()
        rendered = _named_type(state, type(obj))
        return state.finish(rendered)
    return _callable_reference(obj)


def _callable_reference(obj: object) -> TypeRef:
    state = _Render()
    state.imports.add(("collections.abc", "Callable"))
    name = alias_for("collections.abc", "Callable")
    try:
        signature = inspect.signature(typing.cast("Callable[..., Any]", obj))
    except (TypeError, ValueError):
        state.degraded = True
        return state.finish(f"{name}[..., Any]")

    hints = _hints_for(obj)
    result = _render(state, hints.get("return", signature.return_annotation))

    positional = []
    precise = True
    for parameter in signature.parameters.values():
        if (
            parameter.kind
            in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
            or parameter.default is not inspect.Parameter.empty
        ):
            precise = False
            break
        annotation = hints.get(parameter.name, parameter.annotation)
        positional.append(_render(state, annotation))

    if not precise:
        # The return type is still faithful; only the parameter list is elided,
        # which `...` states honestly rather than inventing a shape.
        return state.finish(f"{name}[..., {result}]")
    return state.finish(f"{name}[[{', '.join(positional)}], {result}]")
