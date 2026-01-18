# Plugin System

SPOC's plugin system provides a powerful mechanism for extending application functionality at runtime. Plugins allow you to inject custom behavior, middleware, hooks, and other extensible components into your framework without modifying core application code.

## What are Plugins?

Plugins in SPOC are:

- **Runtime-loaded modules** - Loaded dynamically when the framework starts
- **Organized by groups** - Categorized by function (middleware, hooks, database, etc.)
- **Configurable** - Defined in both TOML and Python settings
- **URI-based** - Referenced using dot-notation paths like `myapp.middleware.auth`
- **Ordered** - Loaded and executed in the sequence they're defined

Unlike components which are discovered through decorator scanning, plugins are explicitly configured and loaded via URIs pointing to specific functions, classes, or modules.

## Plugin Configuration

SPOC supports two ways to configure plugins: TOML-based configuration in `spoc.toml` and Python-based configuration in `settings.py`. Both methods can be used together, with plugins from both sources being merged.

### TOML Configuration

Define plugins in `config/spoc.toml` or `spoc.toml`:

```toml
[spoc]
mode = "development"
debug = true

# Plugin groups organized by function
[spoc.plugins]
# Middleware plugins (request/response processing)
middleware = [
    "myapp.middleware.auth",
    "myapp.middleware.logging",
    "myapp.middleware.cors"
]

# Lifecycle hooks
hooks = [
    "myapp.hooks.startup",
    "myapp.hooks.shutdown"
]

# Database backends
database = [
    "db.backends.postgresql",
    "db.backends.redis"
]

# Cache backends
cache = [
    "cache.backends.memory",
    "cache.backends.redis"
]

# Custom plugin groups
validators = [
    "myapp.validators.email",
    "myapp.validators.phone"
]
```

**Key points:**

- Plugins are organized under `[spoc.plugins]`
- Each group name is arbitrary (you define the groups)
- Plugin URIs must point to importable Python objects
- Plugins are loaded in the order listed

### Python Configuration

Define plugins in `config/settings.py`:

```python
"""Application Settings"""

from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Apps
INSTALLED_APPS: list = [
    "core",
    "auth",
    "api",
]

# Plugins organized by group
PLUGINS: dict = {
    "middleware": [
        "core.middleware.request_id",
        "core.middleware.timing",
        "auth.middleware.authentication",
    ],

    "hooks": [
        "core.hooks.database_connect",
        "core.hooks.cache_warmup",
    ],

    "database": [
        "db.backends.sqlite3",
    ],

    "validators": [
        "core.validators.required",
        "core.validators.email",
    ],
}

# Other settings...
DEBUG = True
```

**Key points:**

- `PLUGINS` must be a dictionary
- Keys are group names (strings)
- Values are lists of URI strings
- Plugins from settings.py merge with plugins from spoc.toml

### Configuration Merging

When both TOML and Python configurations define plugins, they are merged:

**config/spoc.toml:**
```toml
[spoc.plugins]
middleware = ["myapp.middleware.cors"]
hooks = ["myapp.hooks.startup"]
```

**config/settings.py:**
```python
PLUGINS: dict = {
    "middleware": ["myapp.middleware.auth"],
    "database": ["db.backends.postgres"],
}
```

**Resulting merged plugins:**
```python
{
    "middleware": [
        "myapp.middleware.cors",      # From TOML
        "myapp.middleware.auth",      # From settings.py
    ],
    "hooks": [
        "myapp.hooks.startup",        # From TOML
    ],
    "database": [
        "db.backends.postgres",       # From settings.py
    ],
}
```

## How Framework Loads Plugins

The Framework loads plugins automatically during initialization:

### Loading Process

1. **Configuration Loading** - Framework reads spoc.toml and settings.py
2. **Plugin Collection** - `_collect_plugins()` merges plugins from both sources
3. **URI Resolution** - Each URI is resolved using `importer.load_from_uri()`
4. **Group Organization** - Plugins are organized in an OrderedDict by group
5. **Storage** - Plugins are stored in `framework.plugins`

### Internal Implementation

```python
# From framework.py
def _collect_plugins(self) -> Dict[str, OrderedDict[str, Any]]:
    """Collect and load all configured plugins."""
    plugins = self.config.project.get("plugins", {})
    plug_dict: Dict[str, OrderedDict[str, Any]] = {}

    # Merge plugins from settings.PLUGINS
    for group, mods in self.config.settings.PLUGINS.items():
        if group not in plugins:
            plugins[group] = []
        plugins[group].extend(mods)

    # Load each plugin via URI
    if plugins:
        for group, modules in plugins.items():
            if group not in plug_dict:
                plug_dict[group] = OrderedDict()
            for mod_uri in modules:
                if mod_uri not in plug_dict[group]:
                    plug_dict[group][mod_uri] = self.importer.load_from_uri(mod_uri)

    return plug_dict
```

### What Gets Loaded

When you specify a plugin URI like `myapp.middleware.auth`, the framework:

1. Splits the URI into module path and attribute: `myapp.middleware` + `auth`
2. Imports the module: `importlib.import_module("myapp.middleware")`
3. Gets the attribute: `getattr(module, "auth")`
4. Returns the object (function, class, or module)

This means the plugin can be:

- A function
- A class
- A class instance
- A module
- Any Python object

## Accessing Plugins

Once the framework is initialized, access plugins through `framework.plugins`:

### Basic Access

```python
from pathlib import Path
from spoc.framework import Framework, Schema

# Initialize framework
schema = Schema(modules=["models", "views"])
framework = Framework(base_dir=Path("."), schema=schema)

# Access plugin groups
middleware_plugins = framework.plugins.get("middleware", {})
hook_plugins = framework.plugins.get("hooks", {})
database_plugins = framework.plugins.get("database", {})

# Plugins are stored as OrderedDict[uri, loaded_object]
for uri, plugin_obj in middleware_plugins.items():
    print(f"Plugin: {uri} -> {plugin_obj}")
```

### Iterating Plugins by Group

```python
# Get all middleware plugins
if "middleware" in framework.plugins:
    for uri, middleware_func in framework.plugins["middleware"].items():
        print(f"Loaded middleware: {uri}")
        # Use the middleware function
        middleware_func()

# Get all database backends
if "database" in framework.plugins:
    for uri, backend_class in framework.plugins["database"].items():
        print(f"Database backend: {uri}")
        # Instantiate the backend
        backend = backend_class()
```

### Using Plugin Data

```python
# Example: Execute all startup hooks
def execute_startup_hooks(framework):
    """Run all registered startup hooks."""
    if "hooks" not in framework.plugins:
        return

    for uri, hook_func in framework.plugins["hooks"].items():
        try:
            print(f"Executing startup hook: {uri}")
            hook_func()
        except Exception as e:
            print(f"Hook {uri} failed: {e}")

# Example: Initialize database connections
def initialize_databases(framework):
    """Initialize all database backends."""
    if "database" not in framework.plugins:
        return

    connections = {}
    for uri, backend_class in framework.plugins["database"].items():
        backend = backend_class()
        connections[uri] = backend.connect()

    return connections
```

## Creating Plugin Packages

### Simple Function Plugin

The simplest plugin is a function:

**myapp/middleware/logging.py:**
```python
"""Logging middleware plugin."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def log_request(request):
    """Log incoming requests."""
    timestamp = datetime.now().isoformat()
    logger.info(f"[{timestamp}] {request.method} {request.path}")
    return request
```

**Configuration:**
```toml
[spoc.plugins]
middleware = ["myapp.middleware.logging.log_request"]
```

### Class-Based Plugin

For stateful plugins, use classes:

**myapp/database/postgres.py:**
```python
"""PostgreSQL database plugin."""

import psycopg2
from typing import Any, Dict

class PostgreSQLBackend:
    """PostgreSQL database backend."""

    def __init__(self):
        self.connection = None
        self.config = {}

    def configure(self, **kwargs):
        """Configure the backend."""
        self.config = kwargs
        return self

    def connect(self):
        """Establish database connection."""
        self.connection = psycopg2.connect(**self.config)
        return self.connection

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self, query: str) -> Any:
        """Execute a query."""
        cursor = self.connection.cursor()
        cursor.execute(query)
        return cursor.fetchall()
```

**Configuration:**
```toml
[spoc.plugins]
database = ["myapp.database.postgres.PostgreSQLBackend"]
```

**Usage:**
```python
# Access the backend class
backend_class = framework.plugins["database"]["myapp.database.postgres.PostgreSQLBackend"]

# Instantiate and configure
backend = backend_class()
backend.configure(
    host="localhost",
    database="myapp",
    user="postgres",
    password="secret"
)

# Connect and use
connection = backend.connect()
results = backend.execute("SELECT * FROM users")
```

### Plugin with Configuration

Create plugins that read configuration from settings:

**myapp/cache/redis_backend.py:**
```python
"""Redis cache backend plugin."""

import redis
from typing import Any, Optional

class RedisCacheBackend:
    """Redis-based cache backend."""

    def __init__(self, framework=None):
        """
        Initialize Redis backend.

        Args:
            framework: Optional framework instance for config access
        """
        self.framework = framework
        self.client = None

        # Load config from framework if available
        if framework:
            redis_config = framework.config.settings.REDIS_CONFIG
            self.configure(**redis_config)

    def configure(self, host="localhost", port=6379, db=0, **kwargs):
        """Configure Redis connection."""
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            **kwargs
        )

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        return self.client.get(key)

    def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache."""
        self.client.setex(key, ttl, value)

    def delete(self, key: str):
        """Delete key from cache."""
        self.client.delete(key)
```

**config/settings.py:**
```python
# Redis configuration
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "max_connections": 10,
}

PLUGINS = {
    "cache": ["myapp.cache.redis_backend.RedisCacheBackend"],
}
```

### Plugin Factory Pattern

For complex initialization, use factory functions:

**myapp/plugins/validators.py:**
```python
"""Validator plugins using factory pattern."""

from typing import Callable, Any
import re

def create_email_validator(domain_whitelist=None) -> Callable:
    """
    Create an email validator with optional domain whitelist.

    Args:
        domain_whitelist: List of allowed domains (e.g., ['example.com'])

    Returns:
        Validator function
    """
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def validate_email(email: str) -> bool:
        """Validate email address."""
        if not email_pattern.match(email):
            return False

        if domain_whitelist:
            domain = email.split('@')[1]
            return domain in domain_whitelist

        return True

    return validate_email

def create_phone_validator(country_code="+1") -> Callable:
    """
    Create a phone number validator for a specific country.

    Args:
        country_code: Country code prefix

    Returns:
        Validator function
    """
    def validate_phone(phone: str) -> bool:
        """Validate phone number."""
        if not phone.startswith(country_code):
            return False

        # Remove country code and check length
        number = phone[len(country_code):].replace("-", "").replace(" ", "")
        return number.isdigit() and len(number) == 10

    return validate_phone
```

**Usage:**
```python
# In your application code
from myapp.plugins.validators import create_email_validator, create_phone_validator

# Create configured validators
email_validator = create_email_validator(domain_whitelist=['company.com'])
phone_validator = create_phone_validator(country_code="+1")

# Use them
is_valid_email = email_validator("user@company.com")  # True
is_valid_email = email_validator("user@other.com")    # False

is_valid_phone = phone_validator("+1-555-123-4567")  # True
```

## Plugin Discovery Patterns

### Module-Level Plugins

Export plugins from module `__init__.py`:

**myapp/middleware/__init__.py:**
```python
"""Middleware plugins."""

from .auth import authenticate
from .logging import log_request
from .cors import handle_cors

# Export all middleware
__all__ = ["authenticate", "log_request", "handle_cors"]
```

**Configuration:**
```toml
[spoc.plugins]
middleware = [
    "myapp.middleware.authenticate",
    "myapp.middleware.log_request",
    "myapp.middleware.handle_cors",
]
```

### Plugin Registry Pattern

Create a registry for automatic plugin discovery:

**myapp/plugins/registry.py:**
```python
"""Plugin registry system."""

from typing import Dict, List, Any, Callable

class PluginRegistry:
    """Central registry for plugins."""

    def __init__(self):
        self._plugins: Dict[str, List[Any]] = {}

    def register(self, group: str):
        """Decorator to register a plugin."""
        def decorator(plugin_obj):
            if group not in self._plugins:
                self._plugins[group] = []
            self._plugins[group].append(plugin_obj)
            return plugin_obj
        return decorator

    def get_plugins(self, group: str) -> List[Any]:
        """Get all plugins in a group."""
        return self._plugins.get(group, [])

    def execute_all(self, group: str, *args, **kwargs):
        """Execute all plugins in a group."""
        results = []
        for plugin in self.get_plugins(group):
            if callable(plugin):
                results.append(plugin(*args, **kwargs))
        return results

# Global registry instance
registry = PluginRegistry()
```

**myapp/middleware/auth.py:**
```python
"""Authentication middleware."""

from myapp.plugins.registry import registry

@registry.register("middleware")
def authenticate(request):
    """Authenticate incoming requests."""
    # Authentication logic
    token = request.headers.get("Authorization")
    if not token:
        raise ValueError("Missing authentication token")
    return request

@registry.register("middleware")
def authorize(request):
    """Check user permissions."""
    # Authorization logic
    user = request.user
    if not user.has_permission("access_api"):
        raise PermissionError("User lacks required permissions")
    return request
```

**Usage in application:**
```python
from myapp.plugins.registry import registry

# Get all middleware plugins
middleware_plugins = registry.get_plugins("middleware")

# Execute all middleware on a request
for middleware in middleware_plugins:
    request = middleware(request)
```

### Dynamic Plugin Loading

Load plugins dynamically based on configuration:

**myapp/plugins/loader.py:**
```python
"""Dynamic plugin loader."""

from pathlib import Path
import importlib
from typing import Any, Dict, List

class PluginLoader:
    """Load plugins dynamically from configuration."""

    def __init__(self, framework):
        self.framework = framework
        self.loaded_plugins: Dict[str, Any] = {}

    def load_plugin(self, uri: str) -> Any:
        """Load a single plugin from URI."""
        if uri in self.loaded_plugins:
            return self.loaded_plugins[uri]

        # Use framework's importer
        plugin = self.framework.importer.load_from_uri(uri)
        self.loaded_plugins[uri] = plugin
        return plugin

    def load_group(self, group: str) -> List[Any]:
        """Load all plugins in a group."""
        plugins = []

        if group in self.framework.plugins:
            for uri, plugin_obj in self.framework.plugins[group].items():
                plugins.append(plugin_obj)

        return plugins

    def initialize_plugin(self, plugin: Any, config: Dict[str, Any]):
        """Initialize a plugin with configuration."""
        if hasattr(plugin, "configure"):
            plugin.configure(**config)
        elif hasattr(plugin, "__init__"):
            # If it's a class, instantiate with config
            if isinstance(plugin, type):
                return plugin(**config)
        return plugin
```

## Best Practices

### 1. Use Descriptive Group Names

Organize plugins by function with clear group names:

```toml
[spoc.plugins]
# Good: Clear, descriptive names
middleware = [...]
request_validators = [...]
response_formatters = [...]
background_tasks = [...]

# Avoid: Vague names
stuff = [...]
things = [...]
misc = [...]
```

### 2. Document Plugin Interfaces

Clearly document what each plugin expects:

```python
"""Email notification plugin.

Expected Interface:
    - Must be callable with signature: notify(recipient: str, message: str)
    - Should return True on success, False on failure
    - May raise NotificationError on fatal errors

Configuration:
    Set EMAIL_CONFIG in settings.py:
    EMAIL_CONFIG = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "username": "user@example.com",
        "password": "secret",
    }
"""

from typing import Protocol

class NotificationPlugin(Protocol):
    """Protocol for notification plugins."""

    def notify(self, recipient: str, message: str) -> bool:
        """Send a notification."""
        ...
```

### 3. Handle Plugin Failures Gracefully

Plugins should not crash the application:

```python
def load_plugins_safely(framework, group: str):
    """Load plugins with error handling."""
    loaded = []

    if group not in framework.plugins:
        return loaded

    for uri, plugin_obj in framework.plugins[group].items():
        try:
            # Initialize plugin
            if isinstance(plugin_obj, type):
                plugin_instance = plugin_obj()
            else:
                plugin_instance = plugin_obj

            loaded.append(plugin_instance)
            print(f"Loaded plugin: {uri}")

        except Exception as e:
            print(f"Failed to load plugin {uri}: {e}")
            # Continue loading other plugins
            continue

    return loaded
```

### 4. Version Your Plugin Interfaces

Use version markers for plugin compatibility:

```python
"""Database plugin interface v2."""

from typing import Protocol, Any

class DatabasePluginV2(Protocol):
    """Database plugin interface version 2."""

    VERSION = "2.0"

    def connect(self) -> Any:
        """Establish connection."""
        ...

    def disconnect(self) -> None:
        """Close connection."""
        ...

    def execute(self, query: str) -> Any:
        """Execute query."""
        ...

    def transaction(self):
        """Context manager for transactions."""
        ...
```

### 5. Separate Configuration from Code

Keep plugin configuration in settings files:

```python
# config/settings.py

# Plugin configurations
CACHE_CONFIG = {
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
    },
    "memory": {
        "max_size": 1000,
    },
}

DATABASE_CONFIG = {
    "postgres": {
        "host": "localhost",
        "database": "myapp",
        "user": "postgres",
    },
}

# Plugin URIs
PLUGINS = {
    "cache": ["myapp.cache.redis.RedisBackend"],
    "database": ["myapp.database.postgres.PostgresBackend"],
}
```

### 6. Test Plugins Independently

Write unit tests for each plugin:

```python
"""Tests for email notification plugin."""

import pytest
from myapp.plugins.notifications import EmailNotifier

def test_email_notifier_success():
    """Test successful email notification."""
    notifier = EmailNotifier()
    notifier.configure(smtp_host="test.example.com")

    result = notifier.notify("user@example.com", "Test message")
    assert result is True

def test_email_notifier_invalid_recipient():
    """Test notification with invalid recipient."""
    notifier = EmailNotifier()

    with pytest.raises(ValueError):
        notifier.notify("invalid-email", "Test message")
```

### 7. Provide Plugin Examples

Include example plugins in documentation:

```python
"""Example middleware plugin.

This is a template for creating middleware plugins.

Usage:
    1. Copy this file to your app's middleware directory
    2. Modify the process() function with your logic
    3. Add to config/settings.py PLUGINS["middleware"]
"""

class ExampleMiddleware:
    """Example middleware plugin template."""

    def __init__(self):
        self.enabled = True

    def configure(self, **kwargs):
        """Configure the middleware."""
        self.enabled = kwargs.get("enabled", True)
        return self

    def process(self, request):
        """
        Process the request.

        Args:
            request: The incoming request object

        Returns:
            Modified request object
        """
        if not self.enabled:
            return request

        # Your middleware logic here
        print(f"Processing request: {request}")

        return request
```

### 8. Document Plugin Dependencies

List required packages for plugins:

```python
"""Redis cache plugin.

Dependencies:
    - redis>=4.0.0

Installation:
    pip install redis

Configuration:
    REDIS_CONFIG = {
        "host": "localhost",
        "port": 6379,
        "db": 0,
    }
"""

try:
    import redis
except ImportError:
    raise ImportError(
        "Redis plugin requires 'redis' package. "
        "Install it with: pip install redis"
    )
```

## Complete Plugin Example

Here's a complete example showing a plugin system for API rate limiting:

### Plugin Implementation

**myapp/plugins/rate_limiter.py:**
```python
"""Rate limiting plugin for API requests."""

from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib

class RateLimiter:
    """Rate limiting plugin."""

    def __init__(self):
        self.limits: Dict[str, dict] = {}
        self.max_requests = 100
        self.window_seconds = 3600

    def configure(self, max_requests=100, window_seconds=3600):
        """Configure rate limits."""
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        return self

    def get_client_key(self, request) -> str:
        """Generate unique key for client."""
        # Use IP address or API key
        client_id = request.headers.get("X-API-Key") or request.remote_addr
        return hashlib.sha256(client_id.encode()).hexdigest()

    def is_allowed(self, request) -> bool:
        """Check if request is allowed."""
        key = self.get_client_key(request)
        now = datetime.now()

        # Initialize tracking for new clients
        if key not in self.limits:
            self.limits[key] = {
                "count": 0,
                "window_start": now,
            }

        # Reset window if expired
        window_start = self.limits[key]["window_start"]
        if now - window_start > timedelta(seconds=self.window_seconds):
            self.limits[key] = {
                "count": 0,
                "window_start": now,
            }

        # Check limit
        if self.limits[key]["count"] >= self.max_requests:
            return False

        # Increment counter
        self.limits[key]["count"] += 1
        return True

    def get_limit_info(self, request) -> dict:
        """Get current limit information for client."""
        key = self.get_client_key(request)

        if key not in self.limits:
            return {
                "remaining": self.max_requests,
                "limit": self.max_requests,
                "reset": int((datetime.now() + timedelta(seconds=self.window_seconds)).timestamp()),
            }

        return {
            "remaining": max(0, self.max_requests - self.limits[key]["count"]),
            "limit": self.max_requests,
            "reset": int((self.limits[key]["window_start"] + timedelta(seconds=self.window_seconds)).timestamp()),
        }
```

### Configuration

**config/settings.py:**
```python
# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "max_requests": 1000,
    "window_seconds": 3600,
}

PLUGINS = {
    "middleware": ["myapp.plugins.rate_limiter.RateLimiter"],
}
```

### Usage in Application

**main.py:**
```python
"""Main application with rate limiting."""

from pathlib import Path
from spoc.framework import Framework, Schema

# Initialize framework
schema = Schema(modules=["models", "views"])
framework = Framework(base_dir=Path("."), schema=schema)

# Get rate limiter plugin
rate_limiter_class = framework.plugins["middleware"]["myapp.plugins.rate_limiter.RateLimiter"]
rate_limiter = rate_limiter_class()

# Configure from settings
config = framework.config.settings.RATE_LIMIT_CONFIG
rate_limiter.configure(**config)

# Use in request handling
def handle_request(request):
    """Handle an API request with rate limiting."""

    # Check rate limit
    if not rate_limiter.is_allowed(request):
        limit_info = rate_limiter.get_limit_info(request)
        return {
            "error": "Rate limit exceeded",
            "limit": limit_info["limit"],
            "reset": limit_info["reset"],
        }, 429

    # Add rate limit headers to response
    limit_info = rate_limiter.get_limit_info(request)
    response_headers = {
        "X-RateLimit-Limit": str(limit_info["limit"]),
        "X-RateLimit-Remaining": str(limit_info["remaining"]),
        "X-RateLimit-Reset": str(limit_info["reset"]),
    }

    # Process request normally
    result = process_api_request(request)

    return result, 200, response_headers

def process_api_request(request):
    """Process the actual API request."""
    return {"status": "success", "data": {}}
```

## Summary

SPOC's plugin system provides:

- **Flexible configuration** via TOML and Python
- **Runtime loading** through URI-based references
- **Group organization** for logical categorization
- **Easy access** through `framework.plugins`
- **Extensibility** without modifying core code

Plugins are ideal for:

- Middleware and request processing
- Lifecycle hooks (startup/shutdown)
- Backend implementations (database, cache)
- Validators and formatters
- Cross-cutting concerns

Follow best practices to create maintainable, testable, and well-documented plugins that extend your SPOC application's capabilities.

## Next Steps

- Learn about [Components](../api/components.md) for decorator-based registration
- Explore [Framework API](../api/framework.md) for plugin access patterns
- Check [App System](../core/app-system.md) for application organization
- Review [Configuration](../getting-started/configuration.md) for settings management
