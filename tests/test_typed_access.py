"""
Typed access to registry records — one test per spec scenario in
typed-component-access.

The accessors are a pure lookup plus a shape check. What they deliberately do
*not* do — inspect an object's members — is asserted here too, because "we chose
not to check that" is a contract, not an omission.
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Protocol

import pytest

import spoc
from spoc import ComponentShapeError, UnknownKindError, UnknownObjectError
from spoc.testing import ProjectTree


class Post:
    """A constructible component."""

    def __init__(self, title: str = "") -> None:
        self.title = title


class SearchIndex:
    """Instances of this are registered as values."""

    def lookup(self, term: str) -> str:
        return term


CALLS: list[str] = []


def list_posts() -> dict[str, int]:
    CALLS.append("list_posts")
    return {"count": 0}


class PostLike(Protocol):
    """What a consumer says it needs — never what the provider declares."""

    title: str

    def __init__(self, title: str = "") -> None: ...


class Unsatisfied(Protocol):
    """Declares members no registered object provides."""

    def nothing_implements_this(self) -> None: ...


@pytest.fixture
def framework():
    fw = spoc.Framework("models", "views", "resources")
    fw.registry.add("models", "blog", "post", Post)
    fw.registry.add("views", "blog", "list_posts", list_posts)
    fw.registry.add("resources", "blog", "search_index", SearchIndex())
    return fw


@pytest.fixture(autouse=True)
def _no_calls():
    CALLS.clear()
    yield
    CALLS.clear()


# ── The object comes back unchanged ───────────────────────────────────────


def test_the_same_object_comes_back(framework):
    assert framework.resolve_type("models:blog.post", PostLike) is Post


def test_value_component_comes_back_identical(framework):
    registered = framework.resolve("resources:blog.search_index").object
    assert framework.resolve_object("resources:blog.search_index", object) is registered


def test_callable_component_is_not_invoked(framework):
    returned = framework.resolve_object("views:blog.list_posts", object)
    assert returned is list_posts
    assert CALLS == []


# ── Shape is checked; structure is not ────────────────────────────────────


def test_shape_mismatch_is_refused_for_a_value(framework):
    with pytest.raises(ComponentShapeError) as exc:
        framework.resolve_type("resources:blog.search_index", PostLike)

    error = exc.value
    assert error.identifier == "resources:blog.search_index"
    assert error.expected == "a constructible object"
    assert error.got == "a value"
    assert "resources:blog.search_index" in str(error)


def test_shape_mismatch_is_refused_for_a_callable(framework):
    with pytest.raises(ComponentShapeError) as exc:
        framework.resolve_type("views:blog.list_posts", PostLike)
    assert exc.value.got == "a callable"


def test_shape_mismatch_is_refused_for_a_constructible(framework):
    with pytest.raises(ComponentShapeError) as exc:
        framework.resolve_object("models:blog.post", PostLike)

    error = exc.value
    assert error.expected == "a value or a callable"
    assert error.got == "a constructible object"


def test_structural_difference_is_not_refused(framework):
    # Nothing implements Unsatisfied. Shapes match, so access succeeds:
    # membership is the type checker's question, not the registry's.
    assert framework.resolve_type("models:blog.post", Unsatisfied) is Post
    assert framework.resolve_object("views:blog.list_posts", Unsatisfied) is list_posts


def test_shape_matches_for_each_accessor(framework):
    assert framework.resolve_type("models:blog.post", PostLike) is Post
    assert framework.resolve_object("views:blog.list_posts", object) is list_posts
    assert framework.resolve_object("resources:blog.search_index", object) is not None


def test_a_class_is_constructible_before_it_is_callable(framework):
    # A class is callable too; the shape checks are ordered so it never
    # reports as one.
    with pytest.raises(ComponentShapeError) as exc:
        framework.resolve_object("models:blog.post", PostLike)
    assert exc.value.got == "a constructible object"


# ── Failure precision is inherited, not re-implemented ────────────────────


def test_unknown_object_name_names_segment_and_candidates(framework):
    with pytest.raises(UnknownObjectError) as exc:
        framework.resolve_type("models:blog.psot", PostLike)

    message = str(exc.value)
    assert "psot" in message
    assert "post" in message


def test_unknown_kind_names_the_declared_set(framework):
    with pytest.raises(UnknownKindError) as exc:
        framework.resolve_type("widgets:blog.post", PostLike)
    assert "widgets" in str(exc.value)


def test_failure_precision_is_identical_for_both_accessors(framework):
    with pytest.raises(UnknownObjectError) as typed:
        framework.resolve_object("views:blog.missing", object)
    with pytest.raises(UnknownObjectError) as untyped:
        framework.resolve("views:blog.missing")
    assert str(typed.value) == str(untyped.value)


# ── Cross-application access stays decoupled ──────────────────────────────


CATALOG_MODELS = """
    from spoc.core.declaration import component

    @component(kind="models")
    class Product:
        price_cents = 2900
"""

ORDERS_VIEWS = """
    from typing import Protocol

    from framework import framework

    class ProductLike(Protocol):
        price_cents: int

    def total(quantity):
        product_cls = framework.resolve_type("models:catalog.product", ProductLike)
        return product_cls.price_cents * quantity
"""

TWO_APP_FRAMEWORK = (
    "import spoc\n"
    "framework = spoc.Framework(\n"
    '    spoc.KindSpec("models", required=False),\n'
    '    spoc.KindSpec("views", depends_on=("models",), required=False),\n'
    ")\n"
)


def test_cross_application_access_imports_nothing_from_the_provider(tmp_path):
    base = ProjectTree(
        apps={
            "catalog": {"models": CATALOG_MODELS},
            "orders": {"views": ORDERS_VIEWS},
        },
        config={"apps": {"development": ["catalog", "orders"]}},
    ).build(tmp_path, "proj")
    (base / "framework.py").write_text(TWO_APP_FRAMEWORK, encoding="utf-8")

    source = (base / "orders" / "views.py").read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert not any("catalog" in name for name in imported), (
        f"orders must not import catalog; found {imported}"
    )
    assert any("framework" in name for name in imported)


def test_cross_application_access_resolves_at_runtime(tmp_path):
    base = ProjectTree(
        apps={
            "catalog": {"models": CATALOG_MODELS},
            "orders": {"views": ORDERS_VIEWS},
        },
        config={"apps": {"development": ["catalog", "orders"]}},
    ).build(tmp_path, "proj")
    (base / "framework.py").write_text(TWO_APP_FRAMEWORK, encoding="utf-8")

    script = (
        f"import sys; sys.path.insert(0, r'{base}')\n"
        "from framework import framework\n"
        f"framework.start(r'{base}')\n"
        "from orders.views import total\n"
        "print(total(2))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(base),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("5800")


def test_examples_keep_their_decoupling_claim():
    """The reference app's comment is a contract; hold it to it."""
    source = Path("examples/apps/orders/views.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "catalog" not in node.module
        elif isinstance(node, ast.Import):
            assert all("catalog" not in a.name for a in node.names)
