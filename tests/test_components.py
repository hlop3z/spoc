"""
Tests for the declaration layer (spec: object-identity).
"""

import pytest

from spoc.components import Components, Internal, component, get_info, is_spoc
from spoc.core.exceptions import (
    InvalidSegmentError,
    MissingNameError,
    UnknownKindError,
)


class TestComponentDecorator:
    def test_conforming_name_defaults_from_dunder_name(self):
        @component
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
        component(obj)

        info = get_info(obj)
        assert info is not None and info.name == expected

    def test_derived_name_that_cannot_conform_still_fails(self):
        """Conversion is not a guess: a leading digit is still an error."""
        with pytest.raises(InvalidSegmentError) as exc:
            component(type("2Cool", (), {}))

        assert "object_name" in str(exc.value)

    def test_explicit_name_overrides(self):
        @component(name="legacy_service")
        class MyService: ...

        info = get_info(MyService)
        assert info is not None and info.name == "legacy_service"

    def test_explicit_name_is_verbatim_and_validated(self):
        """A stated name is never converted — it is used or rejected."""
        with pytest.raises(InvalidSegmentError) as exc:

            @component(name="MyService")
            class Anything: ...

        assert "'MyService'" in str(exc.value)

    def test_instance_requires_explicit_name(self):
        class Service: ...

        with pytest.raises(MissingNameError):
            component(Service())

    def test_instance_with_explicit_name(self):
        class Service: ...

        instance = component(Service(), name="post_repository")
        info = get_info(instance)
        assert info is not None and info.name == "post_repository"

    def test_instance_class_is_never_mutated(self):
        class Service:
            __hash__ = None  # unhashable on purpose

        instance = Service()
        component(instance, name="svc")
        assert type(instance) is Service  # no synthesized subclass

    def test_config_and_metadata_stored(self):
        @component(name="post", config={"a": 1}, metadata={"b": 2})
        class Post: ...

        info = get_info(Post)
        assert info is not None
        assert info.config == {"a": 1}
        assert info.metadata == {"b": 2}

    def test_is_spoc(self):
        @component
        def handler(): ...

        assert is_spoc(handler)
        assert not is_spoc(object())


class TestComponents:
    def test_kinds_are_closed_at_construction(self):
        components = Components("models", "views")
        assert components.kinds == ("models", "views")
        assert not hasattr(components, "add_type")

    def test_kind_segments_validated(self):
        with pytest.raises(InvalidSegmentError):
            Components("Models")

    def test_register_unknown_kind_rejected(self):
        components = Components("models")
        with pytest.raises(UnknownKindError) as exc:
            components.register("modle", name="x")

        assert "'modle'" in str(exc.value)
        assert "models" in str(exc.value)

    def test_register_attaches_kind_metadata(self):
        components = Components("models")

        @components.register("models")
        class Post: ...

        info = components.get_info(Post)
        assert info is not None
        assert info.metadata["type"] == "models"
        assert info.name == "post"

    def test_kind_names_are_case_sensitive(self):
        """No case-folding anywhere: 'MODELS' is simply unknown."""
        components = Components("models")
        with pytest.raises(UnknownKindError):
            components.register("MODELS", name="x")

    def test_is_component(self):
        components = Components("models", "views")

        @components.register("models")
        class Post: ...

        assert components.is_component("models", Post)
        assert not components.is_component("views", Post)
        with pytest.raises(UnknownKindError):
            components.is_component("commands", Post)

    def test_register_none_rejected(self):
        components = Components("models")
        with pytest.raises(ValueError):
            components.register("models", name="x")(None)
