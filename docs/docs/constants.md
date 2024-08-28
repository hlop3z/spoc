# Constant Variables

The following variables are configured within the `spoc.settings` module and can be used to control various aspects of your application's behavior.

```python
from spoc import settings
```

## Constants

- `BASE_DIR`
- `DEBUG`
- `MODE`
- `SPOC`
- `ENV`
- `CONFIG`

These variables provide a centralized way to manage your application's settings, making it easy to adapt to different environments or configurations.

## `BASE_DIR`

**Description**: Represents the base directory of your project. This is often used as a reference point for constructing paths to other directories and files within the project.

```python
from spoc import settings

SOME_PATH = settings.BASE_DIR / "some-path"
```

## `DEBUG`

**Description**: A boolean variable that indicates whether the application is running in debug mode. This is typically used to enable more verbose logging or debugging features during development.

```python
from spoc import settings

if settings.DEBUG:
    print("Debug Enabled")
else:
    print("Debug Disabled")
```

## `MODE`

**Description**: Defines the current operational mode of the application (e.g., `production`, `staging`, `development`). This is useful for enabling or disabling features based on the environment in which the application is running.

```python
from spoc import settings

match settings.MODE:
    case "production":
        print("Production Mode")
    case "staging":
        print("Staging Mode")
    case "development":
        print("Development Mode")
```

## `SPOC`

**Description**: A dictionary-like object containing specific configuration settings for your application. This can be used to store and retrieve custom configuration values, such as feature flags or integration settings.

```python
from spoc import settings

use_authentication = settings.SPOC.get("mode")
```

## `ENV`

**Description**: A dictionary containing environment-specific variables. This is often used to retrieve sensitive information such as API keys or environment variables required for the application to function.

```python
from spoc import settings

print(settings.ENV["my-variable-name"])
```

Here’s an improved version of your text:

## `CONFIG`

**Description**: A dictionary that contains all the **`TOML`** configurations loaded into the framework. This includes configurations from both the `spoc` and `pyproject` files. Use `CONFIG` to access deeper sections of your **`TOML`** configuration files easily.

**Example:**

```python
from spoc import settings

print(settings.CONFIG)
```
