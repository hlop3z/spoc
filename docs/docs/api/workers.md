# Workers

The workers module provides background task management with support for both thread-based and process-based concurrency strategies. It offers a consistent interface for running tasks in the background with proper lifecycle management, error handling, and graceful shutdown capabilities.

## Overview

Workers are designed for running long-running background tasks with different concurrency models:

- **ThreadWorker**: Ideal for I/O-bound tasks that benefit from shared memory access with the main process
- **ProcessWorker**: Best for CPU-bound tasks that need to bypass Python's Global Interpreter Lock (GIL)
- **Server**: Manages multiple workers collectively with signal handling for graceful shutdowns

All workers share a common lifecycle with `setup()`, `main()`, and `teardown()` hooks, supporting both synchronous and asynchronous implementations. The module also includes utilities for working with async code and optionally integrating uvloop for improved async performance.

## API Reference

::: spoc.workers
    options:
      members:
        - AbstractWorker
        - ThreadWorker
        - ProcessWorker
        - Server
        - set_uvloop_if_available
        - run_async_safely
