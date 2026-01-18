"""
Custom exceptions for dynamic module importing system.

This module defines the exception classes used by the dynamic module importer
to provide clear error messages and categorization for different failure modes.
"""


class SpocError(Exception):
    """Base exception for all dynamic import errors."""

    def __init__(self, message: str, module_name: str | None = None) -> None:
        """
        Initialize a new DynamicImportError.

        Args:
            message: The error message.
            module_name: Name of the module that caused the error, if applicable.
        """
        self.module_name = module_name
        super().__init__(
            f"{message} {f'(module: {module_name})' if module_name else ''}"
        )


class AppNotFoundError(SpocError):
    """Raised when a module cannot be found during dynamic import."""

    def __init__(self, module_name: str) -> None:
        """
        Initialize a new ModuleNotFoundError.

        Args:
            module_name: Name of the module that could not be found.
        """
        super().__init__("Module could not be found", module_name)


class ModuleNotCachedError(SpocError):
    """Raised when attempting to access a module that is not in the cache."""

    def __init__(self, module_name: str) -> None:
        """
        Initialize a new ModuleNotCachedError.

        Args:
            module_name: Name of the module that is not cached.
        """
        super().__init__("Module is not cached", module_name)


class CircularDependencyError(SpocError):
    """Raised when a circular dependency is detected during startup/shutdown."""

    def __init__(self, modules: list[str]) -> None:
        """
        Initialize a new CircularDependencyError.

        Args:
            modules: List of modules involved in the circular dependency.
        """
        modules_str = " -> ".join(modules)
        super().__init__(f"Circular dependency detected: {modules_str}")


class LifecycleError(SpocError):
    """Raised when an error occurs during module lifecycle operations."""

    def __init__(self, message: str, module_name: str | None = None) -> None:
        """
        Initialize a new LifecycleError.

        Args:
            message: The error message.
            module_name: Name of the module where the lifecycle error occurred.
        """
        super().__init__(f"Lifecycle error: {message}", module_name)


class ConfigurationError(SpocError):
    """Error in configuration loading or validation."""

    def __init__(
        self,
        message: str,
        config_file: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize a ConfigurationError.

        Args:
            message: Error message
            config_file: The configuration file that caused the error
            original_error: The original exception that caused this error
        """
        self.config_file = config_file
        error_msg = message
        if config_file:
            error_msg = f"{message} in file {config_file}"

        # Store the original error separately, don't pass it to SpocError
        self.original_error = original_error
        super().__init__(error_msg, None)
