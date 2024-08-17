# -*- coding: utf-8 -*-

"""
Abstract Worker (Process & Thread)
"""

import multiprocessing
import threading
import time
from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import Any


class MethodNotFound(Exception):
    """Error: Missing Function"""

    def __init__(
        self,
        class_name: str,
        function_name: str,
        method_type: str = "method",
    ):
        super().__init__(
            f"Class `{class_name}` is missing implementation for {method_type}: `{function_name}`"
        )
        self.class_name = class_name
        self.function_name = function_name


class AbstractWorker(ABC):
    """Abstract Worker"""

    @abstractmethod
    def _start_event(self) -> Any:
        """Create a stop event."""

    def __init__(self, **kwargs: Any):
        self.options = SimpleNamespace(**kwargs)
        self.__stop_event: Any = self._start_event()

    @abstractmethod
    def server(self) -> Any:
        """Perform server actions. This method must be implemented by subclasses."""

    @abstractmethod
    def on_event(self, event_type: str):
        """Event Manager"""

    def run(self):
        """Run Worker"""
        self.on_event("startup")
        while not self.__stop_event.is_set():
            self.server()

    def stop(self):
        """Stop Worker"""
        self.__stop_event.set()
        self.on_event("shutdown")

    @property
    def stop_event(self) -> Any:
        """Worker Stop Event"""
        return self.__stop_event


class BaseProcess(AbstractWorker, multiprocessing.Process):
    """Abstract Process"""

    def __init__(self, **kwargs: Any):
        multiprocessing.Process.__init__(self)
        AbstractWorker.__init__(self, **kwargs)

    def _start_event(self):
        """Create a stop event."""
        return multiprocessing.Event()


class BaseThread(AbstractWorker, threading.Thread):
    """Abstract Thread"""

    def __init__(self, **kwargs: Any):
        threading.Thread.__init__(self)
        AbstractWorker.__init__(self, **kwargs)

    def _start_event(self):
        """Create a stop event."""
        return threading.Event()


class BaseServer(ABC):
    """
    Control multiple workers `Thread(s)` and/or `Process(es)`.
    """

    workers: list[Any] = []
    on_event: Any

    @classmethod
    def add(cls, *workers: Any) -> None:
        """
        Add worker instances to the service.
        """
        cls.workers.extend(workers)

    @classmethod
    def start(cls, is_loop: bool = True) -> None:
        """
        Start all added workers and optionally keep the main thread running until interrupted.
        """
        # Ensure `on_event`
        if not hasattr(cls, "on_event"):
            raise MethodNotFound(
                cls.__name__,
                "on_event",
                "staticmethod or classmethod",
            )

        # Startup
        cls.on_event("startup")
        for worker in cls.workers:
            worker.start()

        # Loop Until (Keyboard-Interrupt)
        if is_loop:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                cls.stop()

    @classmethod
    def stop(cls, cleanup: bool = False) -> None:
        """
        Stop all running workers and optionally remove workers.
        """
        # Workers
        for worker in cls.workers:
            worker.stop()
        # Process & Threads
        for worker in cls.workers:
            if hasattr(worker, "terminate"):
                worker.terminate()
            worker.join()
        # Cleanup
        if cleanup:
            cls.workers.clear()
        # Shutdown
        cls.on_event("shutdown")
