# Installation

This guide will walk you through installing SPOC on your system.

## Prerequisites

SPOC requires **Python 3.13 or higher**. Before installing, ensure you have a compatible Python version:

<!-- termynal -->

```bash
$ python --version
Python 3.13.0
```

!!! info "Python Version"
    SPOC is built to leverage the latest Python features and requires Python >= 3.13. If you need to upgrade Python, visit [python.org](https://www.python.org/downloads/).

## Installation Methods

### Using pip

The simplest way to install SPOC is using pip:

<!-- termynal -->

```bash
$ pip install spoc
---> 100%
Successfully installed spoc
```

### Using uv

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. To install SPOC with uv:

<!-- termynal -->

```bash
$ uv add spoc
Resolved 1 package in 50ms
Downloaded 1 package in 100ms
Installed 1 package in 5ms
 + spoc==0.1.0
```

!!! tip "Why uv?"
    uv is significantly faster than pip and provides better dependency resolution. It's especially useful for large projects with many dependencies.

### Development Installation

If you want to contribute to SPOC or modify it for your needs, you can install it from source:

1. **Clone the repository:**

    <!-- termynal -->

    ```bash
    $ git clone https://github.com/hlop3z/spoc.git
    Cloning into 'spoc'...
    remote: Enumerating objects: 100, done.
    remote: Counting objects: 100% (100/100), done.
    remote: Compressing objects: 100% (75/75), done.
    Receiving objects: 100% (100/100), done.
    ```

2. **Navigate to the project directory:**

    <!-- termynal -->

    ```bash
    $ cd spoc
    ```

3. **Install in editable mode:**

    <!-- termynal -->

    ```bash
    $ pip install -e .
    Obtaining file:///path/to/spoc
    Installing collected packages: spoc
      Running setup.py develop for spoc
    Successfully installed spoc
    ```

    Or with development dependencies:

    <!-- termynal -->

    ```bash
    $ pip install -e ".[dev]"
    Obtaining file:///path/to/spoc
    Installing collected packages: spoc, pytest, ruff
    Successfully installed spoc pytest-9.0.2 ruff-0.14.13
    ```

!!! note "Editable Mode"
    The `-e` flag installs the package in editable mode, meaning changes to the source code are immediately reflected without reinstalling.

## Verifying Installation

After installation, verify that SPOC is correctly installed by importing it in Python:

<!-- termynal -->

```python
$ python
Python 3.13.0 (main, Oct  7 2024, 10:00:00)
>>> import spoc
>>> print(spoc.__version__)
0.1.0
>>> print(spoc.__about__.__title__)
spoc
```

You can also verify the installation by checking the available modules:

```python
>>> from spoc import Framework, Schema
>>> from spoc.components import component
>>> print("SPOC is ready to use!")
SPOC is ready to use!
```

If the import succeeds without errors, SPOC is successfully installed and ready to use!

## Next Steps

Now that you have SPOC installed, you can:

- Follow the [Quick Start](quick-start.md) guide to build your first SPOC application
- Learn about [Configuration](configuration.md) to set up your project
- Explore the [Framework](../core/framework.md) documentation to understand core concepts

## Troubleshooting

### Python Version Issues

If you encounter a version error:

```
ERROR: Package 'spoc' requires a different Python: 3.12.0 not in '>=3.13'
```

You need to upgrade to Python 3.13 or higher. Check your Python version with `python --version` and install the required version.

### Import Errors

If you get an import error after installation:

```python
>>> import spoc
ModuleNotFoundError: No module named 'spoc'
```

Ensure you're using the same Python environment where you installed SPOC. If you're using virtual environments, make sure it's activated.

### Permission Errors

If you encounter permission errors during installation on Linux/macOS:

<!-- termynal -->

```bash
$ pip install --user spoc
Successfully installed spoc
```

The `--user` flag installs the package in your user directory instead of system-wide.

## Virtual Environments

We strongly recommend using a virtual environment to isolate your project dependencies:

### Using venv

<!-- termynal -->

```bash
$ python -m venv .venv
$ source .venv/bin/activate  # On Windows: .venv\Scripts\activate
(.venv) $ pip install spoc
---> 100%
Successfully installed spoc
```

### Using uv

<!-- termynal -->

```bash
$ uv venv
Using Python 3.13.0
Creating virtual environment at: .venv
Activate with: source .venv/bin/activate
$ source .venv/bin/activate  # On Windows: .venv\Scripts\activate
(.venv) $ uv pip install spoc
Resolved 1 package in 50ms
Installed 1 package in 5ms
 + spoc==0.1.0
```

!!! success "Installation Complete"
    You're all set! SPOC is installed and ready to help you build modular monolith applications.
