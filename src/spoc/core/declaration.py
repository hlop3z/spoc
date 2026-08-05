"""
The declaration layer: what a kind is, and how objects are marked as components of one.

A kind is one :class:`KindSpec` — its name, what it loads after, whether apps must
provide it, the metadata contract its components carry, and its lifecycle hooks. Every
attribute of a kind lives on that one record, so there is no second structure keyed by
kind name that could disagree with the first. A bare string is accepted as shorthand for
a spec with all defaults, because requiring a record for an attribute-free kind would tax
the common case to serve the rare one.

Marking is two steps in time. At import, :func:`registrar` hands out a decorator that
attaches an :class:`Internal` marker to the object — cheap, local, no registry involved.
At start, :func:`discover` turns the markers in a loaded module into registry records.
The split is what lets app modules declare components before the framework has booted.

Discovery is loud. Layout is taxonomy: objects in ``<app>/<kind>.py`` must declare that
kind, and the app package name is the namespace. Anything that cannot be registered
raises rather than being quietly skipped.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

from .exceptions import (
    ComponentKindMismatchError,
    MetadataContractError,
    MissingNameError,
    SpocError,
)
from .identity import to_snake_case, validate_segment
from .registry import Registry


@dataclass(frozen=True)
class KindSpec:
    """Everything the kernel knows about one declared kind."""

    name: str
    depends_on: tuple[str, ...] = ()
    required: bool = True
    metadata: type | None = None
    on_startup: Callable[[set[Any]], None] | None = None
    on_shutdown: Callable[[set[Any]], None] | None = None

    def __post_init__(self) -> None:
        validate_segment("kind", self.name)


@dataclass(frozen=True)
class Internal:
    """Declaration marker attached to a component as ``__spoc__``."""

    name: str
    kind: str
    metadata: Any = field(default=None)


def as_kind_spec(kind: str | KindSpec) -> KindSpec:
    """Normalize the bare-string shorthand into a full :class:`KindSpec`."""
    return kind if isinstance(kind, KindSpec) else KindSpec(name=kind)


def check_metadata(spec: KindSpec, obj_name: str, meta: Any) -> Any:
    """Check metadata against the contract its kind declares."""
    if spec.metadata is None:
        if meta is not None:
            raise MetadataContractError(spec.name, obj_name, None, meta)
        return None
    if not isinstance(meta, spec.metadata):
        raise MetadataContractError(spec.name, obj_name, spec.metadata, meta)
    return meta


def component(
    obj: Any = None, *, kind: str, name: str | None = None, meta: Any = None
) -> Any:
    """Low-level marker: attach an :class:`Internal` to an object."""

    def decorator(target: Any) -> Any:
        if target is None:
            raise ValueError("Cannot register None as a component")
        if name is not None:
            resolved = name
        else:
            intrinsic = getattr(target, "__name__", None)
            resolved = to_snake_case(intrinsic) if intrinsic is not None else None
        if resolved is None:
            raise MissingNameError(target)
        validate_segment("object_name", resolved)
        target.__spoc__ = Internal(name=resolved, kind=kind, metadata=meta)
        return target

    return decorator(obj) if obj is not None else decorator


def registrar(spec: KindSpec) -> Callable[..., Any]:
    """Build the registration handle for one declared kind."""

    def register(obj: Any = None, *, name: str | None = None, meta: Any = None) -> Any:
        def decorator(target: Any) -> Any:
            label = name or getattr(target, "__name__", repr(target))
            check_metadata(spec, label, meta)
            return component(target, kind=spec.name, name=name, meta=meta)

        return decorator(obj) if obj is not None else decorator

    register.__doc__ = f"Register an object as a {spec.name!r} component."
    return register


def is_spoc(obj: Any) -> bool:
    """True if `obj` carries a SPOC declaration marker."""
    return isinstance(getattr(obj, "__spoc__", None), Internal)


def get_info(obj: Any) -> Internal | None:
    """The declaration marker for `obj`, or None."""
    info = getattr(obj, "__spoc__", None)
    return info if isinstance(info, Internal) else None


def _owns_marker(obj: Any) -> bool:
    """True if ``__spoc__`` is attached to `obj` itself rather than inherited."""
    try:
        return "__spoc__" in vars(obj)
    except TypeError:  # no __dict__, so the marker can only be inherited
        return False


def _declared_objects(
    module: ModuleType, module_name: str
) -> list[tuple[str, Any, Internal]]:
    """Marked objects belonging to `module` — imports declared elsewhere are skipped.

    Ownership is the marker's attachment point: an instance or subclass of a decorated
    class inherits ``__spoc__`` through attribute lookup, but only the object the
    decorator was applied to carries it in its own ``__dict__``. Inherited markers are
    not declarations.
    """
    found: list[tuple[str, Any, Internal]] = []
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        obj = getattr(module, attr_name)
        info = getattr(obj, "__spoc__", None)
        if not isinstance(info, Internal):
            continue
        if not _owns_marker(obj):
            continue  # inherited from a decorated class — not a declaration
        if (inspect.isclass(obj) or inspect.isfunction(obj)) and (
            getattr(obj, "__module__", module_name) != module_name
        ):
            continue  # imported, declared elsewhere
        found.append((attr_name, obj, info))
    return found


def discover(registry: Registry, module: ModuleType, module_name: str) -> None:
    """Register every component declared in `module` into `registry`."""
    declared = _declared_objects(module, module_name)
    if not declared:
        return

    pkg, _, location_kind = module_name.rpartition(".")
    if not pkg:
        raise SpocError(
            "Cannot derive a namespace: components must live in an app "
            "package (<app>.<kind>), not a top-level module",
            module_name,
        )
    namespace = validate_segment("namespace", pkg.split(".")[0])

    for attr_name, obj, info in declared:
        if info.kind != location_kind:
            raise ComponentKindMismatchError(
                info.name or attr_name, info.kind, location_kind, module_name
            )
        registry.add(
            kind=location_kind,
            namespace=namespace,
            name=info.name,
            obj=obj,
            metadata=info.metadata,
        )
