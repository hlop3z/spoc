# -*- coding: utf-8 -*-
"""
components.py

The declaration layer: decorators that mark objects as SPOC components.

Usage:
    from spoc import Components

    components = Components("models", "views")

    @components.register("models")
    class post:  # names must already conform: lowercase snake_case
        ...

    # Objects without a conforming __name__ need an explicit name —
    # identity is never inferred and never normalized:
    @components.register("models", name="user_account")
    class UserAccount:
        ...

    # Instances have no intrinsic name, so a name is always required:
    components.register("models", repo, name="post_repository")

Declaration attaches an :class:`Internal` marker; discovery (the importer)
turns markers into registry records at startup. The kind set is closed at
construction — there is no way to add a kind at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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

    The object's identity comes from ``name``, or from ``__name__`` when that
    already conforms to the segment grammar. It is never inferred from the
    execution environment and never normalized.

    Raises:
        MissingNameError: If the object has no ``__name__`` and no explicit
            name was given.
        InvalidSegmentError: If the resolved name violates the grammar.
    """

    def decorator(target_obj: Any) -> Any:
        resolved = name if name is not None else getattr(target_obj, "__name__", None)
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

    Examples:
        >>> components = Components("commands", "models")
        >>> @components.register("commands")
        ... def sync_users():
        ...     ...
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
            name: Explicit object_name segment. Required for objects without
                a conforming ``__name__``; validated, never normalized.
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
