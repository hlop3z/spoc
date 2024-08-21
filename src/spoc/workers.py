# -*- coding: utf-8 -*-

"""
Abstract Worker (Process & Thread)
"""

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

    Attributes:
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

    server: Any
    options: Any

    @abstractmethod
    def _start_event(self) -> Any:
        """Create a stop event."""

    def __init__(self, **kwargs: Any):
        self.options = SimpleNamespace(**kwargs)
        self.__stop_event: Any = self._start_event()

        # Ensure `server`
        if not hasattr(self, "server"):
            raise MethodNotFoundError(
                self.__class__.__name__,
                "server",
                "method",
            )

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
    all_pids: set = set()
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
        if is_loop:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                cls.stop(True)

    @classmethod
    def stop(cls, force_stop: bool = False, forced_delay: int = 1) -> None:
        """
        Stop all running workers.
        """
        # Workers
        for worker in cls.workers:
            worker.stop()

        # Process & Threads
        for worker in cls.workers:
            if hasattr(worker, "terminate"):
                worker.terminate()
            # worker.join()

        # Shutdown
        cls.on_event("shutdown")
        if force_stop:
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

    @classmethod
    def clear(cls) -> None:
        """Workers(list) & PIDS(set) Cleanup"""
        cls.workers.clear()
        cls.all_pids.clear()

    @staticmethod
    def exit() -> None:
        """Exit Main Process"""
        os.kill(os.getpid(), signal.SIGINT)
