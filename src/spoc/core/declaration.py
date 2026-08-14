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
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Protocol, cast, overload

from .exceptions import (
    ComponentKindMismatchError,
    IdentityDivergenceError,
    MetadataContractError,
    MissingNameError,
    UnmarkableObjectError,
)
from .identity import compose, to_snake_case, validate_segment
from .registry import Registry


@dataclass(frozen=True)
class KindSpec:
    """Everything the kernel knows about one declared kind."""

    name: str
    depends_on: tuple[str, ...] = ()
    required: bool = True
    metadata: type | None = None
    #: Hooks may be plain functions or coroutine functions on the same
    #: attribute; a coroutine hook is dispatched by the asynchronous
    #: lifecycle path (``astart``/``ashutdown``) and refused loudly by the
    #: synchronous one.
    #:
    #: Dispatch is **per loaded module**, not once per kind: a hook fires once
    #: for each app module of this kind, receiving that app's components of
    #: this kind as an immutable sequence in canonical-identifier order. A kind
    #: populated only by ``[spoc.plugins]`` entries has no module to dispatch
    #: against, so its hooks never fire.
    on_startup: Callable[[Sequence[Any]], Any] | None = None
    on_shutdown: Callable[[Sequence[Any]], Any] | None = None

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


def check_metadata(spec: KindSpec, obj_name: str, metadata: Any) -> Any:
    """Check metadata against the contract its kind declares."""
    if spec.metadata is None:
        if metadata is not None:
            raise MetadataContractError(spec.name, obj_name, None, metadata)
        return None
    if not isinstance(metadata, spec.metadata):
        raise MetadataContractError(spec.name, obj_name, spec.metadata, metadata)
    return metadata


@overload
def component[T](
    obj: T, /, *, kind: str, name: str | None = None, metadata: Any = None
) -> T: ...
@overload
def component(
    obj: None = None, *, kind: str, name: str | None = None, metadata: Any = None
) -> Decorator: ...
def component(
    obj: Any = None, *, kind: str, name: str | None = None, metadata: Any = None
) -> Any:
    """Low-level marker: attach an :class:`Internal` to an object.

    Typed like a kind's handle, and for the reason :class:`KindHandle` records:
    marking returns the same object, so erasing its type here would erase every
    decorated class at its declaration site — and a stub derived from that would
    promise ``type[Any]`` while every runtime assertion still passed.
    """

    def decorator(target: Any) -> Any:
        if target is None:
            raise ValueError("Cannot register None as a component")
        if name is not None:
            resolved: str | None = name
            derived_from = None
        else:
            intrinsic = getattr(target, "__name__", None)
            resolved = to_snake_case(intrinsic) if intrinsic is not None else None
            derived_from = intrinsic
        if resolved is None:
            raise MissingNameError(target)
        validate_segment("object_name", resolved, derived_from=derived_from)
        try:
            target.__spoc__ = Internal(name=resolved, kind=kind, metadata=metadata)
        except (AttributeError, TypeError) as exc:
            raise UnmarkableObjectError(target, str(exc)) from exc
        return target

    return decorator(obj) if obj is not None else decorator


class Decorator(Protocol):
    """The decorator the parameterized form returns: identity, type preserved."""

    def __call__[T](self, target: T, /) -> T: ...


class KindHandle(Protocol):
    """A kind's registration handle, which states the kind it registers.

    Carrying the kind on the handle is what lets a reader tell one apart from
    any other callable a module happens to export, without matching on names or
    docstrings. Stub generation relies on exactly that when it mirrors a
    composition root.

    Registration is *identity*: marking an object returns that same object, so
    the handle is typed to give back exactly what it was given. Typing it as
    returning ``Any`` would erase every decorated class at its declaration site
    — and then a generated stub promising ``type[Product]`` would be promising
    ``type[Any]``, which is how a stub comes to lie while every assertion about
    it still passes.
    """

    __spoc_kind__: str

    @overload
    def __call__[T](
        self, obj: T, /, *, name: str | None = None, metadata: Any = None
    ) -> T: ...
    @overload
    def __call__(
        self, obj: None = None, *, name: str | None = None, metadata: Any = None
    ) -> Decorator: ...


def registrar(spec: KindSpec) -> KindHandle:
    """Build the registration handle for one declared kind."""

    def register(
        obj: Any = None, *, name: str | None = None, metadata: Any = None
    ) -> Any:
        def decorator(target: Any) -> Any:
            # `getattr` is typed `Any` whatever the attribute is, and both arms
            # here are text — `__name__` where the target has one, its `repr`
            # where it does not.
            derived = cast("str", getattr(target, "__name__", repr(target)))
            label = name or derived
            check_metadata(spec, label, metadata)
            return component(target, kind=spec.name, name=name, metadata=metadata)

        return decorator(obj) if obj is not None else decorator

    register.__doc__ = f"Register an object as a {spec.name!r} component."
    handle = cast("KindHandle", register)
    handle.__spoc_kind__ = spec.name
    return handle


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


def discover(
    registry: Registry, module: ModuleType, module_name: str, namespace: str
) -> None:
    """Register every component declared in `module` into `registry`.

    The namespace is the caller's statement — the final segment of the app's
    declared module path — never parsed back out of the module name.

    Layout is taxonomy, and that is what tells a *use* from a *claim*. A marked
    object appearing in a module of some other kind — ``from .models import
    repo`` inside ``views.py`` — is an ordinary import and is skipped. Two
    modules of the *same* kind both holding it is a second claim: for classes
    and functions ``__module__`` already settled which one declared it (they
    were filtered out before this loop), but an instance carries no such marker,
    so registering it here would hand it whichever namespace loaded first. That
    is refused instead.
    """
    declared = _declared_objects(module, module_name)
    if not declared:
        return

    location_kind = module_name.rpartition(".")[2]
    namespace = validate_segment("namespace", namespace)

    for attr_name, obj, info in declared:
        prior = registry.identifier_of(obj)
        if info.kind != location_kind:
            if prior is not None:
                continue  # imported into another kind's module — a use
            raise ComponentKindMismatchError(
                info.name or attr_name, info.kind, location_kind, module_name
            )
        if prior is not None:
            requested = compose(location_kind, namespace, info.name)
            if prior != requested:
                raise IdentityDivergenceError(prior, requested)
            continue  # the same claim twice — idempotent, nothing to do
        registry.add(
            kind=location_kind,
            namespace=namespace,
            object_name=info.name,
            obj=obj,
            metadata=info.metadata,
        )
