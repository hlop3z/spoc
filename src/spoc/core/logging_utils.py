"""
Lazy Logging Utility

Purpose:
    Provides reusable, singleton-safe logging with lazy string formatting for
    performance and compatibility with linters like pylint.

Usage:
    logger = LazyLogger("my.module")
    logger.info("Processing %s items", count)

Errors:
    - Raises ValueError if an unsupported log level is passed to `log`.
"""

import logging
from types import MappingProxyType
from typing import Any, Literal, Optional, Union

from .singleton import SingletonMeta

LogLevel = Literal["debug", "info", "warning", "error"]


class LazyLogger(metaclass=SingletonMeta):
    """
    Thread-safe singleton wrapper around Python's logging, ensuring
    consistent, lazy-evaluated log messages with minimal overhead.
    """

    _VALID_LEVELS = MappingProxyType(
        {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }
    )

    def __init__(self, logger_name: str):
        """
        Initializes a LazyLogger.

        Args:
            logger_name: The name used to retrieve the logger via `logging.getLogger`.
        """
        self.logger: logging.Logger = logging.getLogger(logger_name)

    def log(
        self,
        level: LogLevel,
        message: str,
        *args: Any,
        exc_info: Union[bool, Exception, None] = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Logs a message using the given level with lazy formatting.

        Args:
            level: One of 'debug', 'info', 'warning', 'error'.
            message: Message format string.
            *args: Arguments for message formatting.
            exc_info: Include exception details.
            stack_info: Include stack summary.
            stacklevel: Call stack depth.
            extra: Structured logging metadata.

        Raises:
            ValueError: If the log level is not supported.
        """
        if level not in self._VALID_LEVELS:
            raise ValueError(f"Unsupported log level: {level}")

        log_method = getattr(self.logger, level)
        if args:
            log_method(
                message,
                *args,
                exc_info=exc_info,
                stack_info=stack_info,
                stacklevel=stacklevel,
                extra=extra,
            )
        else:
            log_method(
                "%s",
                message,
                exc_info=exc_info,
                stack_info=stack_info,
                stacklevel=stacklevel,
                extra=extra,
            )

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug-level message."""
        self.log("debug", message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an info-level message."""
        self.log("info", message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning-level message."""
        self.log("warning", message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log an error-level message."""
        self.log("error", message, *args, **kwargs)
