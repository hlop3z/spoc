# Configuration

SPOC provides a flexible and powerful configuration system that combines TOML files, Python modules, and environment-specific settings. This guide covers how to configure your SPOC application effectively.

## Overview

The SPOC configuration system consists of three main components:

1. **spoc.toml** - TOML-based project configuration
2. **Settings Module** - Python-based settings (settings.py, config.py, or configuration.py)
3. **Environment Files** - Mode-specific environment variables (.env/*.toml)

These components are loaded and merged into a `Config` object that's available throughout your application.

## Configuration Loading

### The Config Object

The `Config` dataclass is a frozen (immutable) container that holds all configuration data:

```python
from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class Config:
    """Configuration container for the framework."""

    project: Dict[str, Any]      # From spoc.toml
    settings: Any                # From settings.py
    environment: Any             # From .env/*.toml
```

### Loading Functions

SPOC provides three core functions for loading configuration:

#### load_spoc_toml(base_dir)

Loads and validates the SPOC TOML configuration file.

```python
from pathlib import Path
from spoc.core.config_loader import load_spoc_toml

config = load_spoc_toml(Path("./my_project"))
# Returns: dict with validated SPOC configuration
```

**Search Locations:**

1. `{base_dir}/config/spoc.toml`
2. `{base_dir}/spoc.toml`

If no file is found, returns a default minimal configuration with a warning.

#### load_configuration(base_dir)

Discovers and imports the Python settings module.

```python
from pathlib import Path
from spoc.core.config_loader import load_configuration

settings = load_configuration(Path("./my_project"))
# Returns: ModuleType with settings attributes
```

**Search Locations:**

The function searches for these module names in order:

- `settings`
- `config`
- `configuration`

In these directories:

1. `{base_dir}/config/`
2. `{base_dir}/conf/`
3. `{base_dir}/` (project root)

Supports both:

- Python files: `settings.py`, `config.py`, `configuration.py`
- Python packages: `settings/__init__.py`, `config/__init__.py`

#### load_environment(base_dir, mode)

Loads environment-specific configuration from TOML files.

```python
from pathlib import Path
from spoc.core.config_loader import load_environment

env = load_environment(Path("./my_project"), "development")
# Returns: dict with environment variables
```

**Search Locations:**

1. `{base_dir}/config/.env/{mode}.toml`
2. `{base_dir}/.env/{mode}.toml`

Falls back to `default.toml` if mode-specific file is not found.

## Project Structure

A typical SPOC project configuration looks like this:

```
my_project/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Python settings module
│   ├── spoc.toml            # SPOC configuration
│   └── .env/                # Environment variables
│       ├── development.toml
│       ├── staging.toml
│       ├── production.toml
│       └── default.toml
├── apps/
│   ├── auth/
│   ├── core/
│   └── api/
└── main.py
```

## spoc.toml Configuration

The `spoc.toml` file defines your project's core configuration using TOML format.

### Basic Structure

```toml
# Application Configuration
[spoc]
mode = "development"  # Options: development, staging, production
debug = true

# Installed Apps by Mode
[spoc.apps]
production = ["auth", "core"]
staging = ["auth", "core", "admin"]
development = ["auth", "core", "admin", "demo"]

# Additional Components (Plugins and Hooks)
[spoc.plugins]
middleware = ["demo.extras.middleware"]
hooks = ["demo.extras.hook"]
database = ["db.backends.sqlite3", "db.backends.postgres"]
```

### Configuration Schema

The SPOC configuration must follow this schema:

```python
{
    "spoc": {
        "mode": str,        # Application mode
        "debug": bool,      # Debug flag
        "apps": dict,       # Apps by mode
        "plugins": dict     # Plugin groups
    }
}
```

### Application Modes

SPOC supports three application modes with cascading app loading:

- **production**: Loads only production apps
- **staging**: Loads staging + production apps
- **development**: Loads development + staging + production apps

Example:

```toml
[spoc]
mode = "development"

[spoc.apps]
production = ["auth", "core"]
staging = ["admin"]
development = ["demo", "debug_toolbar"]
```

In development mode, SPOC will load: `demo`, `debug_toolbar`, `admin`, `auth`, `core`

### Plugins Configuration

Plugins are organized into groups. Each group can contain multiple plugin URIs:

```toml
[spoc.plugins]
middleware = [
    "myapp.middleware.auth",
    "myapp.middleware.logging",
    "myapp.middleware.cors"
]

hooks = [
    "myapp.hooks.startup",
    "myapp.hooks.shutdown"
]

database = [
    "db.backends.sqlite3",
    "db.backends.postgres"
]
```

Plugins are loaded using URI format and can be combined with settings-based plugins.

## Settings Module

The settings module is a Python file or package containing your application configuration.

### Basic Settings File

Create a `config/settings.py` file:

```python
"""Application Settings"""

from pathlib import Path

# Base Directory
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Installed Apps
INSTALLED_APPS: list = [
    "core",
    "auth",
    "api",
]

# Plugins
PLUGINS: dict = {
    "middleware": ["demo.extras.middleware"],
    "hooks": ["demo.extras.hook"],
}

# Database Configuration
DATABASE = {
    "driver": "sqlite3",
    "name": BASE_DIR / "db.sqlite3",
    "options": {
        "timeout": 30,
        "check_same_thread": False,
    }
}

# Security Settings
SECRET_KEY = "your-secret-key-here"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Application Settings
DEBUG = True
LOG_LEVEL = "INFO"
```

### Settings Discovery

SPOC automatically discovers your settings module in these locations:

**As a Python file:**

```
config/settings.py
config/config.py
config/configuration.py
conf/settings.py
settings.py  # project root
```

**As a Python package:**

```
config/settings/__init__.py
config/config/__init__.py
```

### Accessing Settings

Once the framework is initialized, access settings through the config object:

```python
from spoc.framework import Framework, Schema

framework = Framework(base_dir=Path("./"), schema=schema)

# Access settings
database = framework.config.settings.DATABASE
debug_mode = framework.config.settings.DEBUG
apps = framework.config.settings.INSTALLED_APPS
```

## Environment Variables

Environment-specific configuration is stored in TOML files within the `.env` directory.

### Environment File Structure

```
config/.env/
├── development.toml   # Development environment
├── staging.toml       # Staging environment
├── production.toml    # Production environment
└── default.toml       # Default fallback
```

Or alternatively:

```
.env/
├── development.toml
├── staging.toml
├── production.toml
└── default.toml
```

### Environment File Format

Each environment file uses TOML format with an `[env]` section:

**config/.env/development.toml:**

```toml
[env]
DATABASE_URL = "postgresql://localhost/myapp_dev"
DEBUG = "true"
API_KEY = "dev-key-1234"
CACHE_BACKEND = "redis://localhost:6379/0"
LOG_LEVEL = "DEBUG"
```

**config/.env/production.toml:**

```toml
[env]
DATABASE_URL = "postgresql://prod-server/myapp"
DEBUG = "false"
API_KEY = "prod-key-secure"
CACHE_BACKEND = "redis://prod-cache:6379/0"
LOG_LEVEL = "WARNING"
SENTRY_DSN = "https://xxx@sentry.io/yyy"
```

**config/.env/default.toml:**

```toml
[env]
DATABASE_URL = "sqlite:///default.db"
DEBUG = "false"
LOG_LEVEL = "INFO"
```

### Accessing Environment Variables

Access environment variables through the config object:

```python
from spoc.framework import Framework, Schema

framework = Framework(base_dir=Path("./"), schema=schema)

# Access environment variables
db_url = framework.config.environment.get("DATABASE_URL")
debug = framework.config.environment.get("DEBUG") == "true"
api_key = framework.config.environment.get("API_KEY")
```

## Complete Configuration Example

Here's a complete example showing all configuration components working together:

### Project Structure

```
my_project/
├── config/
│   ├── settings.py
│   ├── spoc.toml
│   └── .env/
│       ├── development.toml
│       ├── production.toml
│       └── default.toml
├── apps/
│   ├── core/
│   ├── auth/
│   └── api/
└── main.py
```

### config/spoc.toml

```toml
[spoc]
mode = "development"
debug = true

[spoc.apps]
production = ["core", "auth"]
staging = ["api"]
development = ["demo"]

[spoc.plugins]
middleware = ["core.middleware.auth", "core.middleware.logging"]
```

### config/settings.py

```python
"""Application Settings"""

from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Apps installed via Python settings
INSTALLED_APPS: list = [
    "core",
    "auth",
]

# Plugins defined in Python
PLUGINS: dict = {
    "database": ["db.backends.sqlite3"],
    "cache": ["cache.backends.memory"],
}

# Database Configuration
DATABASE = {
    "driver": "sqlite3",
    "name": BASE_DIR / "db.sqlite3",
}

# Security
SECRET_KEY = "dev-secret-key-change-in-production"
ALLOWED_HOSTS = ["*"]

# Application
DEBUG = True
LOG_LEVEL = "DEBUG"
```

### config/.env/development.toml

```toml
[env]
DATABASE_URL = "sqlite:///dev.db"
DEBUG = "true"
API_KEY = "dev-api-key"
REDIS_URL = "redis://localhost:6379/0"
```

### config/.env/production.toml

```toml
[env]
DATABASE_URL = "postgresql://prod-db/myapp"
DEBUG = "false"
API_KEY = "prod-api-key-secure"
REDIS_URL = "redis://prod-redis:6379/0"
SENTRY_DSN = "https://xxx@sentry.io/yyy"
```

### main.py

```python
"""Main Application Entry Point"""

from pathlib import Path
from spoc.framework import Framework, Schema

# Define application schema
schema = Schema(
    modules=["models", "views", "services"],
    dependencies={
        "views": ["models"],
        "services": ["models"],
    },
    hooks={
        "models": {
            "startup": lambda m: print(f"Models loaded: {m.__name__}"),
        }
    }
)

# Initialize framework
framework = Framework(
    base_dir=Path(__file__).parent,
    schema=schema,
    echo=True
)

# Access configuration
print(f"Mode: {framework.config.project['mode']}")
print(f"Debug: {framework.config.settings.DEBUG}")
print(f"Database: {framework.config.environment.get('DATABASE_URL')}")
print(f"Installed Apps: {framework.installed_apps}")

# Use the framework
# ... your application logic ...

# Shutdown
framework.shutdown()
```

## Configuration Best Practices

### 1. Separate Concerns

- **spoc.toml**: Project structure, apps, plugins
- **settings.py**: Application constants, defaults
- **.env/*.toml**: Environment-specific secrets and URLs

### 2. Use Modes Effectively

Organize apps by deployment stage:

```toml
[spoc.apps]
production = ["core", "auth", "api"]           # Essential apps
staging = ["admin", "monitoring"]              # Testing/admin
development = ["debug_toolbar", "demo", "dev"] # Development tools
```

### 3. Keep Secrets in Environment Files

Never commit sensitive data to spoc.toml or settings.py:

```toml
# Good: In .env/production.toml (add to .gitignore)
[env]
SECRET_KEY = "real-secret-key"
API_KEY = "sensitive-api-key"
```

```python
# Bad: In settings.py (committed to git)
SECRET_KEY = "my-secret-key"  # Don't do this!
```

### 4. Use Type Hints in Settings

Make your settings.py type-safe:

```python
from pathlib import Path
from typing import Dict, List

BASE_DIR: Path = Path(__file__).resolve().parent.parent
INSTALLED_APPS: List[str] = ["core", "auth"]
DATABASE: Dict[str, Any] = {"driver": "sqlite3"}
DEBUG: bool = True
```

### 5. Provide Defaults

Always provide sensible defaults:

```python
# Settings with defaults
LOG_LEVEL = "INFO"
CACHE_TIMEOUT = 300
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
```

### 6. Document Configuration

Add comments to explain non-obvious settings:

```python
# Number of worker threads for background tasks
# Increase for high-load environments
WORKER_THREADS = 4

# Session timeout in seconds
# Default: 30 minutes
SESSION_TIMEOUT = 1800
```

## Troubleshooting

### Configuration Not Found

If you see:

```
ConfigurationError: Could not find configuration module
```

**Solution:** Ensure you have one of these files:

- `config/settings.py`
- `config/config.py`
- `settings.py` (in project root)

### Invalid TOML

If you see:

```
ConfigurationError: Invalid TOML format in spoc.toml
```

**Solution:** Validate your TOML syntax. Common issues:

- Missing quotes around strings
- Incorrect bracket syntax
- Missing commas in arrays

### Missing Required Keys

If you see:

```
ConfigurationError: Missing required key: spoc.mode
```

**Solution:** Ensure spoc.toml has all required fields:

```toml
[spoc]
mode = "development"
debug = true

[spoc.apps]
# At least an empty dict

[spoc.plugins]
# At least an empty dict
```

### Environment File Not Loading

If environment variables aren't loading:

1. Check the mode in spoc.toml matches your .env file name
2. Verify the .env directory structure
3. Ensure the file has `[env]` section

## Next Steps

- Learn about [Quick Start](quick-start.md) to build your first SPOC app
- Explore [Framework](../api/framework.md) to understand how configuration is used
- Check out [Components](../api/components.md) for registering application components

## Related Documentation

- [Installation](installation.md) - Setting up SPOC
- [Framework API](../api/framework.md) - Framework configuration usage
- [Components API](../api/components.md) - Component registration
