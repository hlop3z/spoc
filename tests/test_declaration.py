"""
Tests for the declaration layer (specs: object-identity, framework-declaration,
component-registry).

Covers the marker, the per-kind record, and the metadata contract that replaced the
untyped configuration channel.
"""

from dataclasses import dataclass

import pytest

from spoc.core.declaration import (
    Internal,
    KindSpec,
    as_kind_spec,
    component,
    discover,
    get_info,
    is_spoc,
    registrar,
)
from spoc.core.exceptions import (
    IdentityDivergenceError,
    InvalidSegmentError,
    MetadataContractError,
    MissingNameError,
)


@dataclass(frozen=True)
class ModelMeta:
    table: str


@dataclass(frozen=True)
class ViewMeta:
    route: str


class TestComponentMarker:
    def test_conforming_name_defaults_from_dunder_name(self):
        @component(kind="views")
        def list_users(): ...

        info = get_info(list_users)
        assert isinstance(info, Internal)
        assert info.name == "list_users"

    @pytest.mark.parametrize(
        "class_name,expected",
        [
            ("Post", "post"),
            ("MyService", "my_service"),
            ("UserAccount", "user_account"),
            ("CommentThread", "comment_thread"),
            ("HTTPServer", "http_server"),
            ("Post2", "post2"),
        ],
    )
    def test_derived_class_name_is_converted_to_snake_case(self, class_name, expected):
        """A PEP 8 class name yields the conventional identifier segment."""
        obj = type(class_name, (), {})
        component(obj, kind="models")

        info = get_info(obj)
        assert info is not None and info.name == expected

    def test_derived_name_that_cannot_conform_still_fails(self):
        """Conversion is not a guess: a leading digit is still an error."""
        with pytest.raises(InvalidSegmentError) as exc:
            component(type("2Cool", (), {}), kind="models")

        assert "object_name" in str(exc.value)

    def test_explicit_name_overrides(self):
        @component(kind="models", name="legacy_service")
        class MyService: ...

        info = get_info(MyService)
        assert info is not None and info.name == "legacy_service"

    def test_explicit_name_is_verbatim_and_validated(self):
        """A stated name is never converted — it is used or rejected."""
        with pytest.raises(InvalidSegmentError) as exc:

            @component(kind="models", name="MyService")
            class Anything: ...

        assert "'MyService'" in str(exc.value)

    def test_instance_requires_explicit_name(self):
        class Service: ...

        with pytest.raises(MissingNameError):
            component(Service(), kind="models")

    def test_instance_with_explicit_name(self):
        class Service: ...

        instance = component(Service(), kind="models", name="post_repository")
        info = get_info(instance)
        assert info is not None and info.name == "post_repository"

    def test_instance_class_is_never_mutated(self):
        class Service:
            __hash__ = None  # unhashable on purpose

        instance = Service()
        component(instance, kind="models", name="svc")
        assert type(instance) is Service  # no synthesized subclass

    def test_kind_is_a_field_not_a_metadata_key(self):
        """The kind travels as its own field, not smuggled through a string key."""

        @component(kind="models", name="post")
        class Post: ...

        info = get_info(Post)
        assert info is not None
        assert info.kind == "models"
        assert info.metadata is None

    def test_register_none_rejected(self):
        with pytest.raises(ValueError):
            component(kind="models", name="x")(None)

    def test_is_spoc(self):
        @component(kind="views")
        def handler(): ...

        assert is_spoc(handler)
        assert not is_spoc(object())


class TestKindSpec:
    def test_bare_string_shorthand_expands_to_defaults(self):
        spec = as_kind_spec("models")
        assert spec == KindSpec(name="models")
        assert spec.required is True
        assert spec.depends_on == ()
        assert spec.metadata is None

    def test_spec_passes_through_unchanged(self):
        spec = KindSpec("views", depends_on=("models",), required=False)
        assert as_kind_spec(spec) is spec

    def test_kind_name_validated_at_construction(self):
        with pytest.raises(InvalidSegmentError):
            KindSpec("Models")

    def test_spec_is_frozen(self):
        spec = KindSpec("models")
        with pytest.raises(AttributeError):
            spec.required = False  # ty: ignore[invalid-assignment]

    def test_attributes_ride_the_one_record(self):
        """Every per-kind attribute lives on the spec, not a parallel structure."""
        spec = KindSpec(
            "models",
            depends_on=("schemas",),
            required=False,
            metadata=ModelMeta,
        )
        assert spec.depends_on == ("schemas",)
        assert spec.required is False
        assert spec.metadata is ModelMeta


class TestMetadataContract:
    def test_conforming_metadata_is_stored(self):
        register = registrar(KindSpec("models", metadata=ModelMeta))

        @register(meta=ModelMeta(table="posts"))
        class Post: ...

        info = get_info(Post)
        assert info is not None
        assert info.metadata == ModelMeta(table="posts")

    def test_wrong_metadata_type_rejected(self):
        register = registrar(KindSpec("models", metadata=ModelMeta))
        with pytest.raises(MetadataContractError) as exc:

            @register(meta=ViewMeta(route="/posts"))
            class Post: ...

        message = str(exc.value)
        assert "models" in message
        assert "ModelMeta" in message and "ViewMeta" in message

    def test_no_contract_means_no_metadata_accepted(self):
        """A kind stating no contract closes the untyped channel entirely."""
        register = registrar(KindSpec("views"))
        with pytest.raises(MetadataContractError) as exc:

            @register(meta={"anything": 1})
            class Listing: ...

        assert "declares no metadata contract" in str(exc.value)

    def test_no_contract_and_no_metadata_is_fine(self):
        register = registrar(KindSpec("views"))

        @register
        class Listing: ...

        info = get_info(Listing)
        assert info is not None and info.metadata is None

    def test_contract_declared_but_metadata_omitted_is_rejected(self):
        register = registrar(KindSpec("models", metadata=ModelMeta))
        with pytest.raises(MetadataContractError):

            @register
            class Post: ...

    def test_there_is_no_second_free_form_channel(self):
        """The removed `config=` escape hatch is gone, not renamed."""
        register = registrar(KindSpec("models", metadata=ModelMeta))
        with pytest.raises(TypeError):
            register(config={"a": 1})


class TestRegistrarHandle:
    def test_bare_and_named_forms(self):
        register = registrar(KindSpec("models"))

        @register
        class CommentThread: ...

        @register(name="legacy_user")
        class UserAccount: ...

        thread, account = get_info(CommentThread), get_info(UserAccount)
        assert thread is not None and account is not None
        assert thread.name == "comment_thread"
        assert account.name == "legacy_user"

    def test_handle_marks_with_its_own_kind(self):
        register = registrar(KindSpec("views"))

        @register
        class Listing: ...

        info = get_info(Listing)
        assert info is not None and info.kind == "views"


class TestDiscovery:
    def test_namespace_is_the_callers_statement_not_parsed(self):
        """Discovery registers under the namespace it is told, wherever the
        module name came from — nothing is parsed back out of it."""
        from types import ModuleType

        from spoc.core.registry import Registry

        module = ModuleType("some.deep.pkg.models")

        @component(kind="models")
        class Post: ...

        Post.__module__ = "some.deep.pkg.models"
        setattr(module, "Post", Post)  # noqa: B010

        registry = Registry(("models",))
        discover(registry, module, "some.deep.pkg.models", "pkg")

        assert [c.identifier for c in registry] == ["models:pkg.post"]

    def test_instance_of_a_decorated_class_is_not_a_declaration(self):
        """An instance inherits ``__spoc__`` from its class; only the class declares."""
        from types import ModuleType

        from spoc.core.registry import Registry

        module = ModuleType("blog.models")

        @component(kind="models")
        class Post: ...

        Post.__module__ = "blog.models"
        setattr(module, "Post", Post)  # noqa: B010
        setattr(module, "default_post", Post())  # noqa: B010

        registry = Registry(("models",))
        discover(registry, module, "blog.models", "blog")

        assert [c.identifier for c in registry] == ["models:blog.post"]

    def test_subclass_inheriting_a_marker_is_not_a_declaration(self):
        """A subclass of a decorated class carries the marker but did not declare."""
        from types import ModuleType

        from spoc.core.registry import Registry

        module = ModuleType("blog.models")

        @component(kind="models")
        class Post: ...

        class DraftPost(Post): ...

        for cls in (Post, DraftPost):
            cls.__module__ = "blog.models"
            setattr(module, cls.__name__, cls)

        registry = Registry(("models",))
        discover(registry, module, "blog.models", "blog")

        assert [c.identifier for c in registry] == ["models:blog.post"]

    def test_a_registered_instance_may_be_imported_by_another_kinds_module(self):
        """`from .models import repo` inside `views.py` is a use, not a claim.

        Layout is taxonomy: a marked object appearing in a module of some other
        kind was imported to be used. Only two modules of the *same* kind
        holding it is an ambiguous claim.
        """
        from types import ModuleType

        from spoc.core.registry import Registry

        class Repository: ...

        repo = component(Repository(), kind="models", name="repo")

        models = ModuleType("blog.models")
        setattr(models, "repo", repo)  # noqa: B010
        views = ModuleType("blog.views")
        setattr(views, "repo", repo)  # noqa: B010

        registry = Registry(("models", "views"))
        discover(registry, models, "blog.models", "blog")
        discover(registry, views, "blog.views", "blog")

        assert [c.identifier for c in registry] == ["models:blog.repo"]

    def test_imported_instance_is_refused_not_silently_re_namespaced(self):
        """A re-exported instance is a loud failure, not a load-order coin toss.

        An instance carries no module of its own, so the second module claiming
        it would register it under *that* app's namespace. Whichever app loaded
        first would win, silently.
        """
        from types import ModuleType

        from spoc.core.registry import Registry

        class Repository: ...

        repo = component(Repository(), kind="models", name="repo")

        blog = ModuleType("blog.models")
        setattr(blog, "repo", repo)  # noqa: B010
        shop = ModuleType("shop.models")
        setattr(shop, "repo", repo)  # noqa: B010

        registry = Registry(("models",))
        discover(registry, blog, "blog.models", "blog")

        with pytest.raises(IdentityDivergenceError) as exc:
            discover(registry, shop, "shop.models", "shop")
        message = str(exc.value)
        assert "models:blog.repo" in message
        assert "models:shop.repo" in message
        assert [c.identifier for c in registry] == ["models:blog.repo"]

    def test_re_exported_instance_under_the_same_identity_is_idempotent(self):
        """The same claim twice is not a conflict — only a differing one is."""
        from types import ModuleType

        from spoc.core.registry import Registry

        class Repository: ...

        repo = component(Repository(), kind="models", name="repo")

        first = ModuleType("blog.models")
        setattr(first, "repo", repo)  # noqa: B010
        second = ModuleType("blog.models")
        setattr(second, "repo", repo)  # noqa: B010

        registry = Registry(("models",))
        discover(registry, first, "blog.models", "blog")
        discover(registry, second, "blog.models", "blog")

        assert [c.identifier for c in registry] == ["models:blog.repo"]
