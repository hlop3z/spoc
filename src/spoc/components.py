# -*- coding: utf-8 -*-
"""
components.py

The declaration layer: markers that tag objects as SPOC components.

:class:`Components` is **internal** — it is not exported from the package.
Authors reach this layer through ``Framework.kind()``, which owns a
``Components`` instance and returns its decorator per kind:

    import spoc

    framework = spoc.Framework("models", "views")
    model = framework.kind("models")

    # A PEP 8 class name is converted to its snake_case identifier:
    @model
    class UserAccount:      # → user_account
        ...

    # An explicit name is used verbatim — validated, never converted:
    @model(name="legacy_user")
    class UserAccount:
        ...

    # Instances have no intrinsic name, so a name is always required:
    model(repo, name="post_repository")

Declaration attaches an :class:`Internal` marker; discovery (the importer)
turns markers into registry records at start. The kind set is closed at
construction — there is no way to add a kind at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .case_style import to_snake_case
from .core.exceptions import MissingNameError, UnknownKindError
from .core.identifier import validate_segment


@dataclass(frozen=True)
class Internal:
    """
    Declaration marker attached to a component as ``__spoc__``.

    Attributes:
        name: The validated object_name segment for this component.
        config: Component configuration dictionary.
        metadata: Component metadata dictionary; ``metadata["type"]`` is the
            declared kind.
    """

    name: str
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def component(
    obj: Any = None,
    *,
    name: str | None = None,
    config: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """
    Low-level marker: attach an :class:`Internal` to an object.

    Identity comes from ``name`` when given — used verbatim, validated,
    never converted. Otherwise it is *derived* from the object's
    ``__name__`` by converting to snake_case, so a PEP 8 class name
    (``UserAccount``) yields the conventional identifier segment
    (``user_account``). Identity is never inferred from the execution
    environment, and the derived value is validated like any other: a name
    that does not conform even after conversion is an error, not a guess.

    Raises:
        MissingNameError: If the object has no ``__name__`` and no explicit
            name was given.
        InvalidSegmentError: If the resolved name violates the grammar.
    """

    def decorator(target_obj: Any) -> Any:
        if name is not None:
            resolved = name
        else:
            intrinsic = getattr(target_obj, "__name__", None)
            resolved = to_snake_case(intrinsic) if intrinsic is not None else None
        if resolved is None:
            raise MissingNameError(target_obj)
        validate_segment("object_name", resolved)
        setattr(
            target_obj,
            "__spoc__",
            Internal(
                name=resolved,
                config=dict(config or {}),
                metadata=dict(metadata or {}),
            ),
        )
        return target_obj

    if obj is not None:
        return decorator(obj)
    return decorator


def is_spoc(obj: Any) -> bool:
    """True if `obj` carries a SPOC declaration marker."""
    return isinstance(getattr(obj, "__spoc__", None), Internal)


def get_info(obj: Any) -> Internal | None:
    """The declaration marker for `obj`, or None."""
    info = getattr(obj, "__spoc__", None)
    return info if isinstance(info, Internal) else None


class Components:
    """
    A declared, closed set of component kinds and their register decorator.

    Internal: owned by :class:`~spoc.framework.Framework`, which exposes it
    per kind through ``Framework.kind()``. Not exported from the package.
    """

    def __init__(self, *kinds: str) -> None:
        """
        Args:
            *kinds: The kind set, fixed at construction. Each kind must
                conform to the segment grammar; there is no add-at-runtime.
        """
        self._kinds: tuple[str, ...] = tuple(validate_segment("kind", k) for k in kinds)

    @property
    def kinds(self) -> tuple[str, ...]:
        """The declared kind set."""
        return self._kinds

    def register(
        self,
        kind: str,
        obj: Any = None,
        *,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """
        Decorator (or direct call) registering `obj` as a component of `kind`.

        Args:
            kind: A kind from the declared set.
            obj: The object, when used as a direct call.
            name: Explicit object_name segment, used verbatim and validated.
                Omit it to derive the name from ``__name__`` in snake_case.
                Required for objects with no ``__name__`` (instances).
            config: Configuration stored on the record.
            metadata: Extra metadata merged under the declared kind.

        Raises:
            UnknownKindError: If `kind` is not in the declared set.
            MissingNameError: If a nameless object has no explicit name.
            InvalidSegmentError: If the resolved name violates the grammar.
        """
        if kind not in self._kinds:
            raise UnknownKindError(kind, self._kinds)

        meta = {**(metadata or {}), "type": kind}

        def decorator(target_obj: Any) -> Any:
            if target_obj is None:
                raise ValueError("Cannot register None as a component")
            return component(target_obj, name=name, config=config, metadata=meta)

        if obj is not None:
            return decorator(obj)
        return decorator

    def is_spoc(self, obj: Any) -> bool:
        """True if `obj` carries a SPOC declaration marker."""
        return is_spoc(obj)

    def is_component(self, kind: str, obj: Any) -> bool:
        """
        True if `obj` is declared as a component of `kind`.

        Raises:
            UnknownKindError: If `kind` is not in the declared set.
        """
        if kind not in self._kinds:
            raise UnknownKindError(kind, self._kinds)
        info = get_info(obj)
        return info is not None and info.metadata.get("type") == kind

    def get_info(self, obj: Any) -> Internal | None:
        """The declaration marker for `obj`, or None."""
        return get_info(obj)
