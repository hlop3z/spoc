"""
Component discovery: turn declaration markers into registry records.

Layout is taxonomy: objects declared in ``<app>/<kind>.py`` must declare that
kind, and the app package name is the namespace segment. Discovery is loud —
a declared component that cannot be registered (kind/location mismatch,
invalid segment, duplicate identifier, underivable namespace) fails startup
with an error naming the object, its location, and the reason. Nothing is
ever silently dropped.
"""

from __future__ import annotations

import inspect
from types import ModuleType
from typing import Any

from ..components import Internal
from .exceptions import ComponentKindMismatchError, SpocError
from .identifier import validate_segment
from .registry import Registry


def _declared_objects(
    module: ModuleType, module_name: str
) -> list[tuple[str, Any, Internal]]:
    """
    SPOC-declared objects belonging to `module` (imports excluded).

    Classes and functions defined elsewhere and merely imported into the
    module are skipped — they register where they are defined. Instances
    carry no defining module, so being bound in the module is the declaration.
    """
    found: list[tuple[str, Any, Internal]] = []
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        obj = getattr(module, attr_name)
        info = getattr(obj, "__spoc__", None)
        if not isinstance(info, Internal):
            continue
        if (inspect.isclass(obj) or inspect.isfunction(obj)) and (
            getattr(obj, "__module__", module_name) != module_name
        ):
            continue  # imported, declared elsewhere
        found.append((attr_name, obj, info))
    return found


def discover_components(
    registry: Registry, module: ModuleType, module_name: str
) -> None:
    """
    Register every component declared in `module` into `registry`.

    Args:
        registry: The flat registry to populate.
        module: The loaded module object.
        module_name: Its fully-qualified name, ``<app...>.<kind>``.

    Raises:
        SpocError: If the namespace cannot be derived from the module path.
        ComponentKindMismatchError: If a declared kind does not match the
            module's kind (layout is taxonomy).
        InvalidSegmentError: If the namespace violates the segment grammar.
        UnknownKindError: If the module's kind is not in the declared set.
        DuplicateComponentError: If an identifier is already registered to a
            different object.
    """
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
        declared_kind = info.metadata.get("type")
        if declared_kind != location_kind:
            raise ComponentKindMismatchError(
                info.name or attr_name, str(declared_kind), location_kind, module_name
            )
        registry.add(
            kind=location_kind,
            namespace=namespace,
            name=info.name,
            obj=obj,
            config=info.config,
            metadata=info.metadata,
        )
