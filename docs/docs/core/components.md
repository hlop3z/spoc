# Components

SPOC's component system provides a flexible, metadata-driven approach to organizing and managing classes and functions in your application. Components are the fundamental building blocks that enable SPOC's modular architecture.

## What Are Components?

Components are classes or functions that have been tagged with metadata using decorators. This metadata allows SPOC to:

- Identify and categorize different types of objects (models, views, services, etc.)
- Attach configuration data to components
- Discover components automatically from modules
- Organize components into registries for easy access

Think of components as annotated objects that SPOC can recognize and work with systematically.

## The @component Decorator

The `@component` decorator is the simplest way to mark an object as a SPOC component. It attaches metadata to your classes or functions without changing their behavior.

### Basic Usage

```python
from spoc.components import component

@component
class User:
    def __init__(self, name):
        self.name = name
```

This creates a component with empty configuration and metadata dictionaries.

### With Configuration and Metadata

You can attach configuration and metadata when decorating:

```python
@component(
    config={"database": "users_db", "timeout": 30},
    metadata={"type": "model", "version": "1.0"}
)
class User:
    def __init__(self, name):
        self.name = name
```

- **config**: Runtime configuration for the component (database settings, timeouts, etc.)
- **metadata**: Descriptive information about the component (type, version, tags, etc.)

### Direct Application

You can also apply the decorator directly to an existing object:

```python
class Product:
    pass

Product = component(Product, config={"cache": True})
```

### How It Works

The `@component` decorator attaches an `__spoc__` attribute to the decorated object containing an `Internal` dataclass with your config and metadata:

```python
@component(config={"key": "value"})
class MyClass:
    pass

print(MyClass.__spoc__)
# Internal(config={'key': 'value'}, metadata={})
```

## The Components Registry

The `Components` class provides a registry for managing different types of components with type-specific validation and metadata.

### Creating a Registry

Initialize a registry by specifying the component types you want to work with:

```python
from spoc.components import Components

components = Components("model", "view", "service")
```

This creates a registry that can manage three types of components: models, views, and services.

### Registering Components

Use the `register()` method to tag components with a specific type:

```python
@components.register("model")
class User:
    def __init__(self, name):
        self.name = name

@components.register("service", config={"timeout": 60})
class UserService:
    def __init__(self, user_model):
        self.model = user_model
```

The registry automatically:

- Adds `{"type": "model"}` to the component's metadata
- Validates that the type was declared during registry initialization
- Stores any additional configuration you provide

### Type Checking

Check if an object is a component of a specific type:

```python
@components.register("model")
class User:
    pass

@components.register("view")
class UserView:
    pass

# Check component types
components.is_component("model", User)      # True
components.is_component("view", User)       # False
components.is_component("model", UserView)  # False

# Check if any SPOC component
components.is_spoc(User)      # True
components.is_spoc(object())  # False
```

### Adding Types Dynamically

Add new component types to an existing registry:

```python
components = Components("model")

# Add a new type with default metadata
components.add_type("command", default_meta={"async": True})

@components.register("command")
class SyncUsersCommand:
    pass

# The command now has both type and default metadata
info = components.get_info(SyncUsersCommand)
print(info.metadata)
# {'type': 'command', 'async': True}
```

### Building Component Objects

The `builder()` method creates a structured `Component` object from a decorated component:

```python
@components.register("model")
class User:
    pass

component_obj = components.builder(User)

print(component_obj.type)      # "model"
print(component_obj.name)      # "User"
print(component_obj.app)       # Module name (e.g., "myapp")
print(component_obj.uri)       # "myapp_user"
print(component_obj.object)    # The User class itself
print(component_obj.internal)  # Internal(config={}, metadata={'type': 'model'})
```

The `Component` object provides a complete view of the component with all its metadata in a structured format.

## Component and Internal Dataclasses

SPOC uses two dataclasses to store component information:

### Internal

Stores the raw metadata attached to a component:

```python
from spoc.components import Internal

internal = Internal(
    config={"database": "users_db"},
    metadata={"type": "model", "version": "1.0"}
)
```

**Attributes:**

- `config`: Dictionary of configuration data
- `metadata`: Dictionary of metadata

This is what gets attached to your component as the `__spoc__` attribute.

### Component

Represents a complete component with context:

```python
from spoc.components import Component, Internal

component = Component(
    type="model",
    uri="myapp_user",
    app="myapp",
    name="User",
    object=User,  # The actual class
    internal=Internal(config={}, metadata={"type": "model"})
)
```

**Attributes:**

- `type`: Component type identifier (e.g., "model", "view")
- `uri`: Unique resource identifier (app_name in snake_case)
- `app`: Application/module name the component belongs to
- `name`: Component class/function name
- `object`: The actual component object (class or function)
- `internal`: The Internal dataclass with config and metadata

## Discovering Components from Modules

SPOC automatically discovers components when modules are loaded through the framework. The Importer class scans module attributes looking for objects with the `__spoc__` attribute.

### How Discovery Works

When a module is loaded:

1. The Importer scans all public attributes (not starting/ending with `_`)
2. For each attribute with `__spoc__`, it extracts the type from metadata
3. Components are organized by type and stored with their fully-qualified name

For example, in `myapp/models.py`:

```python
from spoc.components import component

@component(metadata={"type": "model"})
class User:
    pass

@component(metadata={"type": "model"})
class Product:
    pass
```

After loading, SPOC stores:

```python
{
    "model": {
        "myapp.User": User,
        "myapp.Product": Product
    }
}
```

## Framework Integration

The Framework class coordinates component loading and provides runtime access to discovered components.

### How Framework Loads Components

When you start a SPOC application:

```python
from pathlib import Path
from spoc.framework import Framework, Schema

schema = Schema(
    modules=["models", "views", "services"],
    dependencies={"views": ["models"], "services": ["models"]},
    hooks={}
)

framework = Framework(
    base_dir=Path("/path/to/myapp"),
    schema=schema
)
```

The framework:

1. Registers all installed apps and their modules
2. Loads modules in dependency order
3. Discovers components in each module
4. Organizes components by type (models, views, services)
5. Makes them available through `framework.components`

### Component Organization

Components are organized hierarchically:

```
framework.components
├── models
│   ├── myapp.User
│   └── myapp.Product
├── views
│   ├── myapp.UserView
│   └── myapp.ProductView
└── services
    └── myapp.UserService
```

## Accessing Components at Runtime

Once the framework has started, you can access discovered components in several ways.

### Through the Framework

Access components via the `components` namespace:

```python
# Get all models
all_models = framework.components.models

# Access a specific component by fully-qualified name
user_model = framework.components.models.get("myapp.User")
```

### Using get_component()

The framework provides a convenience method:

```python
# Get a specific component by type and name
user_model = framework.get_component("model", "myapp.User")
```

### Direct Component Access

Components are regular Python objects, so you can import and use them normally:

```python
from myapp.models import User

# Create an instance
user = User(name="Alice")
```

The component metadata is always accessible through the `__spoc__` attribute:

```python
from myapp.models import User

print(User.__spoc__.config)
print(User.__spoc__.metadata)
```

## Practical Examples

### Example 1: Multi-Tier Application

Organize components by architectural layer:

```python
from spoc.components import Components

# Define component types
components = Components("model", "repository", "service", "controller")

# Data layer
@components.register("model")
class User:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

# Repository layer
@components.register("repository", config={"database": "postgres"})
class UserRepository:
    def find_by_id(self, user_id):
        # Database logic here
        pass

# Service layer
@components.register("service", config={"cache": True})
class UserService:
    def __init__(self, repository):
        self.repository = repository

    def get_user(self, user_id):
        return self.repository.find_by_id(user_id)

# Controller layer
@components.register("controller")
class UserController:
    def __init__(self, service):
        self.service = service
```

### Example 2: Plugin System

Use components to create a plugin system:

```python
from spoc.components import Components

plugins = Components("plugin")
plugins.add_type("plugin", default_meta={"enabled": True})

@plugins.register("plugin", config={"priority": 10})
class AuthenticationPlugin:
    def process(self, request):
        # Authentication logic
        pass

@plugins.register("plugin", config={"priority": 20})
class LoggingPlugin:
    def process(self, request):
        # Logging logic
        pass

# Sort plugins by priority
all_plugins = plugins.get_info(...)
sorted_plugins = sorted(
    all_plugins,
    key=lambda p: p.config.get("priority", 0)
)
```

### Example 3: Feature Flags

Use component metadata for feature management:

```python
from spoc.components import component

@component(
    config={"enabled": True},
    metadata={"feature": "new_dashboard", "version": "2.0"}
)
class NewDashboardView:
    def render(self):
        if not self.__spoc__.config.get("enabled"):
            raise FeatureDisabledError("Dashboard v2 is disabled")
        # Render dashboard
        pass
```

## Best Practices

### 1. Use Meaningful Type Names

Choose component type names that reflect your architecture:

```python
# Good - clear architectural meaning
Components("model", "view", "controller", "service")

# Avoid - vague or inconsistent
Components("thing", "stuff", "MyComponents")
```

### 2. Keep Configuration Separate from Code

Store configuration in config dictionaries, not hardcoded:

```python
# Good
@components.register("service", config={"timeout": 30, "retry": 3})
class APIService:
    def __init__(self):
        config = self.__spoc__.config
        self.timeout = config.get("timeout")
        self.retry = config.get("retry")

# Avoid
@components.register("service")
class APIService:
    def __init__(self):
        self.timeout = 30  # Hardcoded
        self.retry = 3
```

### 3. Use Metadata for Descriptive Information

Metadata should describe the component, not configure it:

```python
# Good - descriptive metadata, runtime config
@component(
    config={"database": "users"},
    metadata={"type": "model", "version": "2.0", "author": "team-backend"}
)
class User:
    pass

# Avoid - mixing runtime config with metadata
@component(
    metadata={"type": "model", "database": "users"}  # Don't put config in metadata
)
class User:
    pass
```

### 4. Validate Component Types

Always declare component types before using them:

```python
# Good
components = Components("model", "service")

@components.register("model")
class User:
    pass

# This will raise KeyError - type not declared
@components.register("repository")  # KeyError!
class UserRepo:
    pass
```

### 5. Use URIs for Component Identification

The component URI provides a stable identifier:

```python
components = Components("model")

@components.register("model")
class User:
    pass

comp = components.builder(User)
# Use the URI as a stable key
component_map = {comp.uri: comp}  # {"myapp_user": Component(...)}
```

## Summary

SPOC's component system provides:

- **Simple decoration**: Tag classes/functions with `@component`
- **Type-safe registries**: Organize components by type with `Components`
- **Rich metadata**: Attach configuration and descriptive information
- **Automatic discovery**: Components are found and loaded automatically
- **Framework integration**: Access components at runtime through the framework
- **Flexibility**: Use components for any organizational pattern you need

By leveraging components, you can build modular, organized applications where SPOC handles the tedious work of discovering, organizing, and providing access to your application's building blocks.
