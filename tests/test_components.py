"""
Tests for the Components class functionality.
"""

import pytest
from typing import Any

from spoc.components import (
    Components,
    Internal,
    component,
    is_component,
    is_spoc,
)


def test_component_decorator():
    """Test that the component decorator properly tags objects."""

    @component(config={"key": "value"}, metadata={"test": True})
    class TestComponent:
        pass

    # Check that the decorator applied correctly
    assert is_spoc(TestComponent)
    assert hasattr(TestComponent, "__spoc__")
    assert TestComponent.__spoc__.config == {"key": "value"}
    assert TestComponent.__spoc__.metadata == {"test": True}


def test_is_component():
    """Test the is_component function works correctly."""

    @component(metadata={"type": "test_type"})
    class TestComponent:
        pass

    assert is_component(TestComponent, {"type": "test_type"})
    assert not is_component(TestComponent, {"type": "wrong_type"})


def test_components_registry():
    """Test that the Components registry works correctly."""
    # Create a registry with two component types
    components = Components("model", "controller")

    # Register a component
    @components.register("model", config={"db": "postgres"})
    class UserModel:
        pass

    # Verify it was registered correctly
    assert components.is_component("model", UserModel)
    assert not components.is_component("controller", UserModel)

    # Test that registering with an unknown type raises an error
    with pytest.raises(KeyError):

        @components.register("unknown")
        class InvalidComponent:
            pass


def test_components_builder():
    """Test the builder method for creating Component objects."""
    components = Components("model")

    @components.register("model")
    class UserModel:
        pass

    component = components.builder(UserModel)
    assert component.type == "model"
    assert component.name == "UserModel"
    assert component.object is UserModel


class TestComponents:
    """Test suite for the components module."""

    def test_component_decorator_simple(self):
        """Test the component decorator in its simplest form."""

        @component
        class TestClass:
            pass

        assert hasattr(TestClass, "__spoc__")
        assert isinstance(TestClass.__spoc__, Internal)
        assert is_spoc(TestClass)
        assert TestClass.__spoc__.config == {}
        assert TestClass.__spoc__.metadata == {}

    def test_component_decorator_with_params(self):
        """Test the component decorator with parameters."""

        config = {"key": "value"}
        metadata = {"type": "test"}

        @component(config=config, metadata=metadata)
        class TestClass:
            pass

        assert hasattr(TestClass, "__spoc__")
        assert isinstance(TestClass.__spoc__, Internal)
        assert is_spoc(TestClass)
        assert TestClass.__spoc__.config == config
        assert TestClass.__spoc__.metadata == metadata

    def test_component_is_callable(self):
        """Test direct application of component decorator."""

        class TestClass:
            pass

        decorated = component(TestClass)
        assert hasattr(decorated, "__spoc__")
        assert is_spoc(decorated)

    def test_is_spoc_function(self):
        """Test the is_spoc function."""

        @component
        class SpocClass:
            pass

        class NonSpocClass:
            pass

        assert is_spoc(SpocClass)
        assert not is_spoc(NonSpocClass)
        assert not is_spoc(None)
        assert not is_spoc(42)

    def test_is_component_function(self):
        """Test the is_component function."""

        metadata = {"type": "test"}

        @component(metadata=metadata)
        class MatchingClass:
            pass

        @component(metadata={"type": "other"})
        class NonMatchingClass:
            pass

        assert is_component(MatchingClass, metadata)
        assert not is_component(NonMatchingClass, metadata)
        assert not is_component(object(), metadata)

    def test_components_registry(self):
        """Test the Components registry functionality."""

        components = Components("service", "model")

        # Test registering a component
        @components.register("service")
        class Service:
            pass

        assert components.is_component("service", Service)
        assert not components.is_component("model", Service)

    def test_components_add_type(self):
        """Test adding component types to an existing registry."""

        components = Components()
        components.add_type("command")
        components.add_type("query", {"description": "A query component"})

        # Register components of the new types
        @components.register("command")
        class Command:
            pass

        @components.register("query")
        class Query:
            pass

        # Verify they were registered correctly
        assert components.is_component("command", Command)
        assert components.is_component("query", Query)

        # Verify default metadata was applied
        assert (
            components.get_info(Query).metadata.get("description")
            == "A query component"
        )

    def test_components_get_info(self):
        """Test getting component information."""

        components = Components("service")

        @components.register("service", config={"timeout": 30})
        class Service:
            pass

        info = components.get_info(Service)
        assert isinstance(info, Internal)
        assert info.config == {"timeout": 30}
        assert info.metadata == {"type": "service"}

        # Test getting info for non-component
        assert components.get_info(object()) is None

    def test_components_builder(self):
        """Test building a Component object from a decorated class."""

        components = Components("controller")

        @components.register("controller")
        class UserController:
            pass

        # Build a component info object
        comp = components.builder(UserController)
        print(comp)

        # Verify component info
        assert components.is_component("controller", UserController)
        assert comp.type == "controller"
        assert comp.name == "UserController"
        assert comp.app == "tests"  # Module name
        assert "tests_user_controller" in comp.uri  # Snake case name

    @pytest.mark.parametrize("invalid_value", [None, 42, "string", lambda: None])
    def test_is_component_with_invalid_values(self, invalid_value: Any):
        """Test is_component with various invalid values."""
        assert not is_component(invalid_value, {"type": "test"})

    def test_component_registry_case_insensitivity(self):
        """Test that component registry is case-insensitive."""
        components = Components("Service")

        @components.register("SERVICE")
        class Service:
            pass

        assert components.is_component("service", Service)
        assert components.is_component("Service", Service)
        assert components.is_component("SERVICE", Service)

    def test_register_component_with_error(self):
        """Test registering a component with an unregistered type raises an error."""
        components = Components("model")

        with pytest.raises(KeyError, match="Component type 'service' not declared"):

            @components.register("service")
            class Service:
                pass

    def test_case_style_method(self):
        """Test the case_style utility method."""
        components = Components()

        # Test different case styles
        assert components.case_style("UserService", mode="snake") == "user_service"
        assert components.case_style("user_service", mode="pascal") == "UserService"
        assert components.case_style("user-service", mode="camel") == "userService"
        assert components.case_style("UserService", mode="kebab") == "user-service"

    def test_complex_component_hierarchy(self):
        """Test registering and retrieving components in a complex hierarchy."""
        # Create a registry with multiple component types
        components = Components("repository", "service", "controller")

        # Register components with dependencies indicated in config
        @components.register("repository")
        class UserRepository:
            pass

        @components.register("service", config={"uses": "UserRepository"})
        class UserService:
            def __init__(self, repo=None):
                self.repo = repo

        @components.register("controller", config={"uses": "UserService"})
        class UserController:
            def __init__(self, service=None):
                self.service = service

        # Check configs
        service_info = components.get_info(UserService)
        controller_info = components.get_info(UserController)

        assert service_info.config.get("uses") == "UserRepository"
        assert controller_info.config.get("uses") == "UserService"
