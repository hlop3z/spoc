# SPOC

<img src="https://raw.githubusercontent.com/hlop3z/spoc/main/docs/docs/assets/images/title.png" alt="title-image" width="100%" />

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Language](https://img.shields.io/github/languages/top/hlop3z/spoc)
![GitHub](https://img.shields.io/github/v/tag/hlop3z/spoc?label=github)
![PyPI](https://img.shields.io/pypi/v/spoc?color=blue)
![Downloads](https://img.shields.io/pypi/dm/spoc?color=darkgreen)

**SPOC** is a Python framework for building **modular monolithic applications**. Inspired by Django's app system, it provides automatic module discovery, dependency management, and lifecycle orchestration.

## Features

- **App-based architecture** - Organize code into self-contained, reusable modules
- **Automatic discovery** - Apps and components are discovered and loaded at runtime
- **Dependency management** - Define module dependencies with automatic load ordering
- **Component registry** - Register and retrieve components using decorators
- **Lifecycle hooks** - Startup and shutdown hooks for proper resource management
- **TOML configuration** - Simple configuration with `spoc.toml`

## Installation

**Requires Python 3.13+**

```bash
pip install spoc
```

## Quick Start

```python
from pathlib import Path
from spoc import Framework, Schema

# Define your application schema
schema = Schema(
    modules=["models", "views"],
    dependencies={"views": ["models"]},
)

# Create and run the framework
framework = Framework(
    base_dir=Path(__file__).parent,
    schema=schema,
)

# Access registered components
print(framework.components.models.values())
```

## Documentation

For detailed documentation, tutorials, and examples:

**[Read the Docs](https://hlop3z.github.io/spoc/)**

## Links

- [PyPI](https://pypi.org/project/spoc)
- [GitHub](https://github.com/hlop3z/spoc)
