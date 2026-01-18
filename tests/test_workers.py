"""
Tests for the workers module.
"""

import asyncio
import threading
import time
from unittest.mock import MagicMock, patch


from spoc.workers import (
    AbstractWorker,
    ProcessWorker,
    Server,
    ThreadWorker,
    run_async_safely,
    set_uvloop_if_available,
)


class TestAbstractWorker:
    """Tests for the AbstractWorker base class."""

    class MockWorker(AbstractWorker):
        """A concrete implementation of AbstractWorker for testing."""

        def _create_stop_signal(self):
            return threading.Event()

        def main(self):
            # Simple implementation that counts until stopped
            self.counter = 0
            while not self._stop_signal.is_set() and self.counter < 5:
                self.counter += 1
                time.sleep(0.01)
            return self.counter

    class AsyncMockWorker(AbstractWorker):
        """A concrete implementation with async main method for testing."""

        def _create_stop_signal(self):
            return threading.Event()

        async def main(self):
            self.counter = 0
            while not self._stop_signal.is_set() and self.counter < 5:
                self.counter += 1
                await asyncio.sleep(0.01)
            return self.counter

    def test_init(self):
        """Test worker initialization."""
        worker = self.MockWorker("MockWorker")
        assert worker.name == "MockWorker"
        assert worker.context is not None
        assert worker._stop_signal is not None
        assert worker._is_async is False
        assert worker._thread_or_process is None

    def test_is_running(self):
        """Test the is_running property."""
        worker = self.MockWorker("MockWorker")
        assert worker.is_running is True
        worker.stop()
        assert worker.is_running is False

    def test_stop(self):
        """Test worker stop method."""
        worker = self.MockWorker("MockWorker")
        assert not worker._stop_signal.is_set()
        worker.stop()
        assert worker._stop_signal.is_set()

    def test_lifecycle_event(self):
        """Test lifecycle event emission."""
        worker = self.MockWorker("MockWorker")
        worker.lifecycle = MagicMock()
        worker._emit_lifecycle_event("test", data="test")
        worker.lifecycle.assert_called_once_with("test", data="test")

    def test_run_sync(self):
        """Test running a synchronous worker."""
        worker = self.MockWorker("MockWorker")
        worker.setup = MagicMock()
        worker.teardown = MagicMock()
        worker.lifecycle = MagicMock()

        worker.run()

        worker.setup.assert_called_once()
        worker.teardown.assert_called_once()
        # Check for startup and shutdown events
        assert worker.lifecycle.call_count >= 2
        # Check that main method executed and counter incremented
        assert hasattr(worker, "counter")
        assert worker.counter == 5

    def test_error_handling(self):
        """Test error handling in worker run method."""

        class ErrorWorker(self.MockWorker):
            def main(self):
                raise ValueError("Test error")

        worker = ErrorWorker("ErrorWorker")

        # Create a spy on lifecycle method
        lifecycle_calls = []

        def lifecycle_spy(event_type, **data):
            lifecycle_calls.append((event_type, data))

        worker.lifecycle = lifecycle_spy

        # Run the worker
        worker.run()

        # Verify that key events were emitted
        events = [call[0] for call in lifecycle_calls]
        assert "startup" in events, "Startup event not emitted"
        assert "shutdown" in events, "Shutdown event not emitted"

        # Find the error event
        error_events = [(evt, data) for evt, data in lifecycle_calls if evt == "error"]
        assert len(error_events) > 0, "Error event not emitted"

        # Verify the exception is in the error data
        assert "exception" in error_events[0][1]
        assert isinstance(error_events[0][1]["exception"], ValueError)


class TestThreadWorker:
    """Tests for the ThreadWorker implementation."""

    class DummyThreadWorker(ThreadWorker):
        """Test ThreadWorker implementation with main method."""

        def main(self):
            """Implement the abstract method."""
            pass

    def test_init(self):
        """Test ThreadWorker initialization."""
        worker = self.DummyThreadWorker(name="TestThread", daemon=True)
        assert worker.name == "TestThread"
        assert worker._thread_or_process is not None
        assert isinstance(worker._thread_or_process, threading.Thread)
        assert worker._thread_or_process.daemon is True
        assert isinstance(worker._stop_signal, threading.Event)

    def test_concrete_worker(self):
        """Test a concrete ThreadWorker implementation."""

        class CounterWorker(ThreadWorker):
            def setup(self):
                self.counter = 0
                self.setup_called = True

            def main(self):
                while not self._stop_signal.is_set() and self.counter < 3:
                    self.counter += 1
                    time.sleep(0.01)

            def teardown(self):
                self.teardown_called = True

        worker = CounterWorker(name="Counter")

        try:
            # Start the worker
            worker.start()

            # Let it run briefly
            time.sleep(0.1)

            # Should have finished counting
            assert worker.counter == 3
            assert worker.setup_called is True

            # Stop the worker
            worker.stop()

            # Wait for thread to terminate
            worker.join(timeout=1.0)

            # Should have called teardown
            assert worker.teardown_called is True
            assert not worker._thread_or_process.is_alive()

        finally:
            # Ensure cleanup
            if worker._thread_or_process and worker._thread_or_process.is_alive():
                worker.stop()
                worker.join(timeout=1.0)


class TestProcessWorker:
    """Tests for the ProcessWorker implementation."""

    class DummyProcessWorker(ProcessWorker):
        """Test ProcessWorker implementation with main method."""

        def main(self):
            """Implement the abstract method."""
            pass

    def test_init(self):
        """Test ProcessWorker initialization."""
        worker = self.DummyProcessWorker(name="TestProcess", daemon=True)
        assert worker.name == "TestProcess"
        assert worker._thread_or_process is not None
        assert worker._thread_or_process.daemon is True

    # Note: Full process worker tests would be more complex due to
    # separate process; focus on initialization for unit tests


class TestServer:
    """Tests for the Server class."""

    def test_init(self):
        """Test Server initialization."""
        server = Server(name="TestServer")
        assert server.name == "TestServer"
        assert server._workers == []
        assert isinstance(server._stop_signal, threading.Event)
        assert not server._stop_signal.is_set()

    def test_add_worker(self):
        """Test adding workers to server."""
        server = Server()

        # Create concrete implementations of ThreadWorker
        class ConcreteWorker1(ThreadWorker):
            def main(self):
                pass

        class ConcreteWorker2(ThreadWorker):
            def main(self):
                pass

        worker1 = ConcreteWorker1("Worker1")
        worker2 = ConcreteWorker2("Worker2")

        server.add_worker(worker1)
        server.add_worker(worker2)

        assert len(server._workers) == 2
        assert worker1 in server._workers
        assert worker2 in server._workers

    def test_start_stop(self):
        """Test starting and stopping workers through server."""
        server = Server()

        # Create mock workers
        worker1 = MagicMock()
        worker2 = MagicMock()

        server.add_worker(worker1)
        server.add_worker(worker2)

        # Start all workers
        server.start()

        worker1.start.assert_called_once()
        worker2.start.assert_called_once()

        # Stop all workers
        server.stop()

        worker1.stop.assert_called_once()
        worker2.stop.assert_called_once()
        assert server._stop_signal.is_set()

    def test_join_all(self):
        """Test joining workers through server."""
        server = Server()

        # Create mock workers
        worker1 = MagicMock()
        worker2 = MagicMock()

        server.add_worker(worker1)
        server.add_worker(worker2)

        # Join all workers
        server.join_all(timeout=2.0)

        worker1.join.assert_called_once()
        worker2.join.assert_called_once()

        # Check that timeout was passed
        assert worker1.join.call_args[1]["timeout"] <= 2.0
        assert worker2.join.call_args[1]["timeout"] <= 2.0

    def test_signal_handler(self):
        """Test signal handler method."""
        server = Server()

        with patch.object(server, "stop") as mock_stop:
            # Call the signal handler
            server._on_signal(None, None)

            # Should call stop
            mock_stop.assert_called_once()


class TestAsyncUtils:
    """Tests for async utility functions."""

    def test_set_uvloop_if_available(self):
        """Test setting uvloop if available."""
        # Just test that the function doesn't raise
        set_uvloop_if_available()

    def test_run_async_safely(self):
        """Test running a coroutine safely."""

        # Create a simple coroutine function
        async def test_coro():
            return 42

        # Test case 1: Running loop exists, patching asyncio.create_task
        with patch("asyncio.get_running_loop") as mock_get_loop:
            # Mock that a loop is available
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.is_running.return_value = True

            with patch("asyncio.create_task") as mock_create_task:
                coro1 = test_coro()
                run_async_safely(coro1)
                # Should have called create_task
                mock_create_task.assert_called_once()
                # Close the coroutine to avoid warning (it was passed to mock)
                coro1.close()

        # Test case 2: No running loop, patching asyncio.run
        with patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")):
            with patch("asyncio.run") as mock_run:
                coro2 = test_coro()
                run_async_safely(coro2)
                # Should have called asyncio.run
                mock_run.assert_called_once()
                # Close the coroutine to avoid warning (it was passed to mock)
                coro2.close()
