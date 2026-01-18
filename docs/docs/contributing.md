# Contributing to SPOC

Thank you for considering contributing to SPOC! This document outlines the process for contributing to the project and how you can help make it better.

## Development Environment

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) (preferred) or pip for package management

### Setting Up for Development

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/yourusername/spoc.git
   cd spoc
   ```

3. Set up a virtual environment and install development dependencies:

   ```bash
   # Using uv
   uv venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv install -e ".[dev]"

   # Using pip
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

4. Set up pre-commit hooks:

   ```bash
   pre-commit install
   ```

## Development Workflow

### Branching Strategy

- `main`: Contains the latest stable version
- `dev`: Development branch for next release
- Feature branches: Create from `dev` with the format `feature/your-feature-name`
- Bugfix branches: Create from `dev` with the format `bugfix/issue-description`

### Making Changes

1. Create a new branch for your changes:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and ensure they adhere to the project's style guidelines

3. Run tests to ensure your changes don't break existing functionality:

   ```bash
   pytest
   ```

4. Run linting and type checking:

   ```bash
   ruff check .
   mypy src
   ```

### Commit Guidelines

- Use clear, descriptive commit messages
- Reference issue numbers in your commit messages where applicable
- Keep commits focused on a single logical change
- Format commit messages as:

  ```
  type(scope): description

  Additional details if necessary
  ```

  Where `type` is one of: feat, fix, docs, style, refactor, test, chore

### Pull Request Process

1. Update the documentation to reflect any changes you've made
2. Ensure all tests pass and code quality checks succeed
3. Push your changes to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a pull request against the `dev` branch
5. In your PR, provide:
   - A clear description of the changes
   - Any relevant issue numbers
   - Notes on any dependencies that were added or removed

## Testing

### Running Tests

Run the test suite with:

```bash
pytest
```

For coverage information:

```bash
pytest --cov=spoc
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with the pattern `test_*.py`
- Test classes should be named `Test*`
- Test methods should be named `test_*`
- Use pytest fixtures where appropriate

## Documentation

### Building Documentation

Build the documentation locally:

```bash
cd docs
mkdocs serve
```

This will start a local server at <http://127.0.0.1:8000/> where you can preview your changes.

### Writing Documentation

- Use clear, concise language
- Include examples where applicable
- Follow Google-style docstrings for Python code
- Update the documentation when you add or modify features

## Style Guidelines

SPOC follows these style guidelines:

- **Code Style**: PEP 8 with a line length of 88 characters (enforced by ruff)
- **Type Hints**: All public functions and methods should have type hints
- **Docstrings**: Google-style docstrings
- **Import Order**:
  1. Standard library imports
  2. Third-party library imports
  3. Local application imports (with a blank line between each group)

## License

By contributing to SPOC, you agree that your contributions will be licensed under the project's license.

## Questions?

If you have any questions about contributing, please open an issue or reach out to the maintainers. We're happy to help!
