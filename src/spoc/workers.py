# -*- coding: utf-8 -*-

"""
Abstract Workers (Process & Thread)
"""

import asyncio
import inspect
import multiprocessing
import os
import signal
import threading
import time
from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import Any


class MethodNotFoundError(Exception):
    """
    Exception raised when a required method is **missing** from a class **implementation**.

    Args:
        class_name (str): Name of the class where the method is missing.
        method_name (str): Name of the missing method.
        method_type (str): Type of the method (e.g., `staticmethod`, `classmethod`, `property`).
            Defaults to `method`.
    """

    def __init__(
        self,
        class_name: str,
        method_name: str,
        method_type: str = "method",
    ):
        super().__init__(
            f"<class '{class_name}'> is missing implementation for {method_type}: `{method_name}`"
        )
        self.class_name = class_name
        self.function_name = method_name


class AbstractWorker(ABC):
    """Abstract Worker"""

    agent: Any = asyncio
    server: Any
    options: Any
    on_event: Any

    @abstractmethod
    def _start_event(self) -> Any:
        """Create a stop event."""

    def _validate_required_methods(self) -> None:
        """Ensure required methods exist in the subclass."""
        required_methods = ["server", "on_event"]
        for method_name in required_methods:
            if not hasattr(self, method_name):
                raise MethodNotFoundError(
                    self.__class__.__name__, method_name, "method"
                )

    def __init__(self, **kwargs: Any):
        self.options = SimpleNamespace(**kwargs)
        self.__stop_event = self._start_event()

        # Ensure `server` and `on_event` methods exist
        self._validate_required_methods()

    def run(self) -> None:
        """Run Worker"""
        self.before()
        if inspect.iscoroutinefunction(self.server):
            # Async Server
            self.agent.run(self.run_async())
        else:
            # Sync Server
            self.run_sync()

    def before(self) -> None:
        """Setup before running server."""

    def run_sync(self) -> None:
        """Run Synchronous Worker"""
        self.on_event("startup")
        job = threading.Thread(target=self.server)
        job.daemon = True
        job.start()
        # Dummy Loop
        while self.active:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                pass
        # After Stop
        self.on_event("shutdown")

    async def run_async(self) -> None:
        """Run Asynchronous Worker"""
        loop = asyncio.get_running_loop()
        await self.on_event("startup")
        loop.create_task(self.server())
        # Dummy Loop
        while self.active:
            try:
                await asyncio.sleep(1)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
        # After Stop
        await self.on_event("shutdown")

    def stop(self):
        """Stop Worker"""
        self.__stop_event.set()

    @property
    def stop_event(self) -> Any:
        """Worker Stop Event"""
        return self.__stop_event

    @property
    def active(self) -> bool:
        """Worker is Active"""
        return not self.__stop_event.is_set()


class BaseProcess(AbstractWorker, multiprocessing.Process):
    """
    Abstract Process

    Example:

    ```python
    class AsyncProcess(spoc.BaseProcess):
        agent: Any = asyncio # Example: `uvloop`

        def before(self) -> None:
            ... # Set uvloop.EventLoopPolicy()

        async def on_event(self, event_type: str):
            ...

        async def server(self):
            while self.active:
                ...


    class SyncProcess(spoc.BaseProcess):
        def on_event(self, event_type: str):
            ...

        def server(self):
            while self.active:
                ...
    ```
    """

    def __init__(self, **kwargs: Any):
        multiprocessing.Process.__init__(self)
        AbstractWorker.__init__(self, **kwargs)

    def _start_event(self):
        """Create a stop event."""
        return multiprocessing.Event()


class BaseThread(AbstractWorker, threading.Thread):
    """
    Abstract Thread

    Example:

    ```python
    class AsyncThread(spoc.BaseThread):
        agent: Any = asyncio # Example: `uvloop`

        def before(self) -> None:
            ... # Set uvloop.EventLoopPolicy()

        async def on_event(self, event_type: str):
            ...

        async def server(self):
            while self.active:
                ...


    class SyncThread(spoc.BaseThread):
        def on_event(self, event_type: str):
            ...

        def server(self):
            while self.active:
                ...
    ```
    """

    def __init__(self, **kwargs: Any):
        threading.Thread.__init__(self)
        AbstractWorker.__init__(self, **kwargs)

    def _start_event(self):
        """Create a stop event."""
        return threading.Event()


class BaseServer(ABC):
    """
    Control multiple workers `Thread(s)` and/or `Process(es)`.

    Example:

    ```python
    import time

    class MyProcess(spoc.BaseProcess):  # BaseThread
        def on_event(self, event_type):
            print("Process | Thread:", event_type)

        def server(self):
            while self.active:
                print("My Server", self.options.name)
                time.sleep(2)

    class MyServer(spoc.BaseServer):
        @classmethod  # or staticmethod
        def on_event(cls, event_type):
            print("Server:", event_type)

    # Press (CTRL + C) to Quit
    MyServer.add(MyProcess(name="One"))
    MyServer.add(MyProcess(name="Two"))
    MyServer.start()
    ```
    """

    workers: list[Any] = []
    all_pids: set = set()
    on_event: Any

    @classmethod
    def clear(cls) -> None:
        """Workers and PIDs cleanup"""
        cls.workers.clear()
        cls.all_pids.clear()

    @staticmethod
    def exit() -> None:
        """Exit main process"""
        os.kill(os.getpid(), signal.SIGINT)

    @classmethod
    def add(cls, *workers: Any) -> None:
        """
        Add worker instances to the service.
        """
        cls.workers.extend(workers)

    @staticmethod
    def _disable_exit_signal() -> None:
        """Wait for cleanup to complete."""

        def handler(*_):
            """Ctrl+C pressed."""

        # Temporarily ignore Ctrl+C
        signal.signal(signal.SIGINT, handler)

    @classmethod
    def start(
        cls, infinite_loop: bool = True, timeout: int = 5, forced_delay: int = 1
    ) -> None:
        """
        Start all added workers and optionally keep a loop running until interrupted.
        """
        # Ensure `on_event`
        if not hasattr(cls, "on_event"):
            raise MethodNotFoundError(
                cls.__name__,
                "on_event",
                "staticmethod or classmethod",
            )

        # Startup
        cls.on_event("startup")

        # Main PID
        cls.all_pids.add(os.getpid())

        # Start Workers
        for worker in cls.workers:
            worker.start()

            # Register PID(s)
            if hasattr(worker, "pid"):
                cls.all_pids.add(worker.pid)
                cls.all_pids.add(os.getppid())
            else:
                cls.all_pids.add(os.getppid())

        # Loop Until (Keyboard-Interrupt)
        if infinite_loop:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                # Disable (Ctrl + C)
                cls._disable_exit_signal()
                # Before Shutdown
                cls.on_event("before_shutdown")
                cls.stop(force_stop=True, timeout=timeout, forced_delay=forced_delay)

    @classmethod
    def stop(
        cls, timeout: int = 5, force_stop: bool = False, forced_delay: int = 1
    ) -> None:
        """
        Stop all running workers.
        """
        is_alive: bool = False

        # Workers
        for worker in cls.workers:
            worker.stop()

        # Stop => Process & Threads
        for worker in cls.workers:
            if hasattr(worker, "join"):
                worker.join(timeout=timeout)  # Wait for the specified delay

        for worker in cls.workers:
            if hasattr(worker, "terminate"):
                worker.terminate()

            if hasattr(worker, "is_alive") and worker.is_alive():
                is_alive = True

        # Shutdown
        cls.on_event("shutdown")
        if force_stop and is_alive:
            cls.force_stop(forced_delay)

    @classmethod
    def force_stop(cls, delay: int = 1) -> None:
        """
        Force to stop.
        """
        main_pid = os.getpid()
        time.sleep(delay)

        # Kill Processes
        for pid in cls.all_pids:
            try:
                if main_pid != pid:
                    os.kill(pid, signal.SIGINT)
            except Exception:
                pass

        # Cleanup
        cls.clear()
