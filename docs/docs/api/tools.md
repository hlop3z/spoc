# Tools

The tools module provides a flexible tool registration and discovery system for Python functions. It enables you to mark functions as discoverable tools with metadata like categories and descriptions, then automatically register and introspect them at runtime.

## Key Features

- **Tool Decorator**: Mark any function as a tool with optional category and description metadata
- **Automatic Discovery**: Scan modules to find all decorated tool functions
- **Rich Metadata**: Extract function signatures, parameter types, defaults, and return types
- **Dynamic Registration**: Build tool registries at runtime for plugin systems and extensible applications

## Use Cases

The tool system is ideal for:

- Building plugin architectures where tools can be dynamically discovered
- Creating command-line interfaces with auto-generated help text
- Implementing chatbot or AI assistant function calling
- Organizing utility functions with categorization and documentation

## Basic Usage

```python
from spoc.tools import tool, register_tools

# Simple tool with default category
@tool
def hello():
    """Say hello"""
    return "Hello, world!"

# Tool with custom category and description
@tool(category="math", description="Add two numbers together")
def add(a: int, b: int) -> int:
    return a + b

# Register all tools in current module
import sys
tools = register_tools(sys.modules[__name__])
```

::: spoc.tools
