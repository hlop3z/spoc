"""
Worker module providing different concurrency strategies for background tasks.

This module implements various worker classes that can run tasks in different
concurrency contexts (threads, processes) with consistent lifecycle management
and error handling. It also provides a server to manage multiple workers.
"""

import asyncio
import inspect
import multiprocessing
import signal
import threading
import time
from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import Any, Coroutine, List, Optional, TypeVar, Union, cast

T = TypeVar("T")
MPEvent = Any  # Represents multiprocessing.Event

try:
    import uvloop

    UVLOOP_INSTALLED = True
except ImportError:
    uvloop = None
    UVLOOP_INSTALLED = False


def set_uvloop_if_available() -> None:
    """Set uvloop as the event loop policy if installed."""
    if UVLOOP_INSTALLED and uvloop:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


# --- Async Safety Bridge ---
def run_async_safely(coro: Coroutine[Any, Any, Any]) -> None:
    """Run coroutine safely whether in an existing event loop or not."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.create_task(coro)
            return
    except RuntimeError:
        pass  # No event loop is running

    set_uvloop_if_available()
    asyncio.run(coro)


# --- Abstract Worker Base ---
class AbstractWorker(ABC):
    """
    Abstract base class for all worker implementations.

    Provides a consistent interface for different worker types (thread, process)
    with unified lifecycle management and error handling.
    """

    @abstractmethod
    def _create_stop_signal(self) -> Union[threading.Event, MPEvent]:
        """Create the appropriate stop signal for the worker type."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.context = SimpleNamespace()
        self._stop_signal = self._create_stop_signal()
        self._is_async = inspect.iscoroutinefunction(self.main)
        self._thread_or_process: Optional[
            Union[threading.Thread, multiprocessing.Process]
        ] = None

    @property
    def is_running(self) -> bool:
        """Return True if the worker is running."""
        return not self._stop_signal.is_set()

    def stop(self) -> None:
        """Signal the worker to stop."""
        self._stop_signal.set()

    def start(self) -> None:
        """Start the worker."""
        if self._thread_or_process is not None:
            self._thread_or_process.start()

    def join(self, timeout: Optional[float] = None) -> None:
        """Join the worker, with optional timeout."""
        if self._thread_or_process is not None:
            self._thread_or_process.join(timeout)
            if self._thread_or_process.is_alive() and isinstance(
                self._thread_or_process, multiprocessing.Process
            ):
                self._thread_or_process.terminate()

    async def _run_async_task(self) -> None:
        """Run the main task asynchronously."""
        try:
            await self.main()
        except KeyboardInterrupt:
            pass

    def _call_setup(self) -> None:
        """Call the setup method, handling async if needed."""
        if inspect.iscoroutinefunction(self.setup):
            run_async_safely(cast(Coroutine[Any, Any, Any], self.setup()))
        else:
            self.setup()

    def _call_teardown(self) -> None:
        """Call the teardown method, handling async if needed."""
        if inspect.iscoroutinefunction(self.teardown):
            run_async_safely(cast(Coroutine[Any, Any, Any], self.teardown()))
        else:
            self.teardown()

    def _emit_lifecycle_event(self, event_type: str, **data: Any) -> None:
        """Emit a lifecycle event to the lifecycle handler."""
        method = self.lifecycle
        if inspect.iscoroutinefunction(method):
            run_async_safely(method(event_type, **data))
        else:
            method(event_type, **data)

    def run(self) -> None:
        """Main run method that handles the worker lifecycle."""
        self._emit_lifecycle_event("startup")
        try:
            self._call_setup()
            if self._is_async:
                run_async_safely(self._run_async_task())
            else:
                try:
                    self.main()
                except KeyboardInterrupt:
                    pass
        # Handle keyboard interrupt gracefully
        except KeyboardInterrupt:
            pass
        # Handle I/O and OS errors
        except (OSError, IOError) as ex:
            self._emit_lifecycle_event("error", exception=ex)
        # pylint: disable=broad-exception-caught
        except Exception as ex:
            # Log unexpected errors via lifecycle events
            # This is intended as a last-resort safety mechanism to prevent
            # worker crashes from taking down the entire application
            self._emit_lifecycle_event("error", exception=ex)
        # pylint: enable=broad-exception-caught
        finally:
            self._call_teardown()
            self._emit_lifecycle_event("shutdown")

    def setup(self) -> None:
        """Setup method called before main. Override in subclasses."""
        # Method intentionally left empty for subclasses to override

    @abstractmethod
    def main(self) -> Any:
        """Main worker method. Must be implemented by subclasses."""

    def teardown(self) -> None:
        """Teardown method called after main. Override in subclasses."""
        # Method intentionally left empty for subclasses to override

    def lifecycle(self, event_type: str, **data: Any) -> None:
        """Lifecycle event handler. Override in subclasses."""
        # Method intentionally left empty for subclasses to override


# --- Threaded Worker ---
class ThreadWorker(AbstractWorker):
    """
    Worker implementation that runs in a thread.

    Useful for I/O-bound tasks or tasks that need to share memory with the main process.
    """

    def __init__(self, name: str = "ThreadWorker", daemon: bool = True) -> None:
        """Initialize a worker that runs in a thread."""
        super().__init__(name)
        self._thread_or_process = threading.Thread(target=self.run, daemon=daemon)

    def _create_stop_signal(self) -> threading.Event:
        """Create a threading.Event as stop signal."""
        return threading.Event()


# --- Process Worker ---
class ProcessWorker(AbstractWorker):
    """
    Worker implementation that runs in a separate process.

    Useful for CPU-bound tasks that benefit from bypassing the GIL.
    """

    def __init__(self, name: str = "ProcessWorker", daemon: bool = True) -> None:
        """Initialize a worker that runs in a separate process."""
        super().__init__(name)
        self._thread_or_process = multiprocessing.Process(
            target=self.run, daemon=daemon
        )

    def _create_stop_signal(self) -> MPEvent:
        """Create a multiprocessing.Event as stop signal."""
        return multiprocessing.Event()


# --- Server to Manage Workers ---
class Server:
    """
    Server to manage multiple workers.

    Provides methods to start, stop, and manage the lifecycle of workers collectively,
    with proper signal handling for graceful shutdowns.
    """

    def _on_signal(self, _signum: int, _frame: Any) -> None:
        """
        Signal handler for SIGINT and SIGTERM.

        Args:
            _signum: The signal number received (unused but required by signal API)
            _frame: Frame object (unused but required by signal API)
        """
        self.stop()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._on_signal)
        signal.signal(signal.SIGTERM, self._on_signal)

    def __init__(self, name: str = "Server") -> None:
        """Initialize a server to manage multiple workers."""
        self.name = name
        self._workers: List[AbstractWorker] = []
        self._stop_signal = threading.Event()
        self._setup_signal_handlers()

    def add_worker(self, worker: AbstractWorker) -> None:
        """Add a worker to be managed by this server."""
        self._workers.append(worker)

    def start(self) -> None:
        """Start all managed workers."""
        for w in self._workers:
            w.start()

    def stop(self) -> None:
        """Stop all managed workers."""
        for w in self._workers:
            w.stop()
        self._stop_signal.set()

    def join_all(self, timeout: float = 5) -> None:
        """Join all workers with a shared timeout."""
        start_time = time.time()
        for w in self._workers:
            remaining = max(0, timeout - (time.time() - start_time))
            w.join(timeout=remaining)

    def run_forever(self) -> None:
        """Run the server until stopped by signal or exception."""
        self.start()
        try:
            while not self._stop_signal.is_set():
                time.sleep(0.5)
        finally:
            self.stop()
            self.join_all()
