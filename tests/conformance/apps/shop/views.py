"""Callable components — one fully annotated, one deliberately not."""

from framework import view


@view
def list_products() -> dict[str, int]:
    return {"count": 2}


@view
def find_product(term: str) -> str:
    return term


@view
def unannotated(anything, *rest):
    """No annotations: the stub must degrade to Any rather than guess."""
    return anything
