"""
Tests for the tools module.
"""

from typing import Any, Dict, List, Optional


from spoc.tools import register_tools, tool


def test_tool_decorator():
    """Test the tool decorator correctly marks functions as tools."""

    @tool
    def sample_tool():
        """A sample tool function."""
        return "sample result"

    # Check that the decorator applied the necessary attributes
    assert hasattr(sample_tool, "__is_tool__")
    assert sample_tool.__is_tool__ is True

    # Check that the function still works normally
    assert sample_tool() == "sample result"

    # Check that the docstring is preserved
    assert sample_tool.__doc__ == "A sample tool function."


def test_tool_decorator_with_parameters():
    """Test tool decorator with parameters."""

    @tool(category="test", description="Custom description")
    def param_tool():
        return "param result"

    # Check basic decorator functionality
    assert hasattr(param_tool, "__is_tool__")
    assert param_tool.__is_tool__ is True

    # Check the custom attributes
    assert hasattr(param_tool, "__tool_category__")
    assert param_tool.__tool_category__ == "test"
    assert hasattr(param_tool, "__tool_description__")
    assert param_tool.__tool_description__ == "Custom description"


def test_register_tools():
    """Test registering tool functions."""

    # Create some tool functions
    @tool(category="math")
    def add(a, b):
        """Add two numbers."""
        return a + b

    @tool(category="math")
    def subtract(a, b):
        """Subtract b from a."""
        return a - b

    @tool(category="text")
    def concat(a, b):
        """Concatenate two strings."""
        return str(a) + str(b)

    # Define a regular function (not a tool)
    def not_a_tool():
        return "not a tool"

    # Create a module-like object with these functions
    class MockModule:
        pass

    mock_module = MockModule()
    mock_module.add = add
    mock_module.subtract = subtract
    mock_module.concat = concat
    mock_module.not_a_tool = not_a_tool

    # Register tools from the mock module
    tools_dict = register_tools(mock_module)

    # Check that all tools were registered
    assert "add" in tools_dict
    assert "subtract" in tools_dict
    assert "concat" in tools_dict

    # Check that non-tools were not registered
    assert "not_a_tool" not in tools_dict

    # Check that categories were preserved
    assert tools_dict["add"]["category"] == "math"
    assert tools_dict["subtract"]["category"] == "math"
    assert tools_dict["concat"]["category"] == "text"

    # Check that function references were preserved
    assert tools_dict["add"]["func"] is add

    # Check that docstrings were captured as descriptions
    assert tools_dict["add"]["description"] == "Add two numbers."

    # Check that parameter info was captured
    assert "params" in tools_dict["add"]
    assert len(tools_dict["add"]["params"]) == 2
    assert tools_dict["add"]["params"][0]["name"] == "a"
    assert tools_dict["add"]["params"][1]["name"] == "b"


def test_register_tools_with_annotations():
    """Test registering tools with type annotations."""

    @tool
    def typed_tool(a: int, b: str, c: Optional[List[Dict[str, Any]]] = None) -> str:
        """A tool with type annotations."""
        return f"{a} {b}"

    # Create a module-like object
    class MockModule:
        pass

    mock_module = MockModule()
    mock_module.typed_tool = typed_tool

    # Register tools
    tools_dict = register_tools(mock_module)

    # Check that type annotations were captured
    assert "typed_tool" in tools_dict
    params = tools_dict["typed_tool"]["params"]

    assert params[0]["name"] == "a"
    assert params[0]["type"] == "int"
    assert not params[0]["optional"]

    assert params[1]["name"] == "b"
    assert params[1]["type"] == "str"
    assert not params[1]["optional"]

    assert params[2]["name"] == "c"
    # For Python 3.13+, Optional types are represented differently
    assert "Optional" in params[2]["type"]
    assert params[2]["optional"]

    # Check return type
    assert tools_dict["typed_tool"]["return_type"] == "str"


def test_register_tools_with_defaults():
    """Test registering tools with default parameter values."""

    @tool
    def default_params(a, b=5, c="default"):
        """A tool with default parameter values."""
        return a + b

    # Create a module-like object
    class MockModule:
        pass

    mock_module = MockModule()
    mock_module.default_params = default_params

    # Register tools
    tools_dict = register_tools(mock_module)

    # Check that default values were captured
    assert "default_params" in tools_dict
    params = tools_dict["default_params"]["params"]

    assert params[0]["name"] == "a"
    assert not params[0]["optional"]
    assert "default" not in params[0]

    assert params[1]["name"] == "b"
    assert params[1]["optional"]
    assert params[1]["default"] == 5

    assert params[2]["name"] == "c"
    assert params[2]["optional"]
    assert params[2]["default"] == "default"


def test_register_tools_with_custom_descriptions():
    """Test registering tools with custom descriptions."""

    @tool(description="Custom tool description")
    def custom_desc():
        """Docstring description."""
        pass

    # Create a module-like object
    class MockModule:
        pass

    mock_module = MockModule()
    mock_module.custom_desc = custom_desc

    # Register tools
    tools_dict = register_tools(mock_module)

    # Custom description should override docstring
    assert tools_dict["custom_desc"]["description"] == "Custom tool description"


def test_register_tools_empty_module():
    """Test registering tools from an empty module."""

    class EmptyModule:
        pass

    empty_module = EmptyModule()

    # Register tools (should return empty dict)
    tools_dict = register_tools(empty_module)

    assert tools_dict == {}
