# Multi-App SPOC Application

A comprehensive example showing how to build a production-ready multi-app SPOC application with users, blog functionality, background workers, and environment-based configuration.

---

## What You'll Learn

This example demonstrates:

- **Multi-app architecture**: Organizing code into separate apps (users, blog)
- **Component types**: Models, views, services with proper separation of concerns
- **Cross-app dependencies**: How apps interact through components
- **Lifecycle hooks**: Database initialization and cleanup
- **Environment variables**: Configuration for different deployment environments
- **Background workers**: Processing tasks asynchronously
- **Dependency injection**: Accessing framework components throughout your app

---

## Project Structure

```
blog_platform/
├── apps/
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── services.py
│   │   └── workers.py
│   └── blog/
│       ├── __init__.py
│       ├── models.py
│       ├── views.py
│       ├── services.py
│       └── workers.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── spoc.toml
│   └── .env.example
├── framework/
│   ├── __init__.py
│   ├── components.py
│   └── database.py
├── main.py
└── requirements.txt
```

---

## Complete Implementation

### 1. Configuration Files

#### `config/settings.py`

```python
"""
Project settings configuration.

Defines the base configuration for the blog platform including
installed apps, database settings, and plugin configuration.
"""

from pathlib import Path

# Base directory of the project
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Apps always installed regardless of environment
INSTALLED_APPS: list = [
    "users",  # User management (authentication, profiles)
    "blog",   # Blog functionality (posts, comments)
]

# Plugin configuration for cross-cutting concerns
PLUGINS: dict = {
    "middleware": [
        # Add middleware plugins here
        # Example: "framework.middleware.LoggingMiddleware"
    ],
    "hooks": [
        # Add hook plugins here
        # Example: "framework.hooks.MetricsHook"
    ],
}

# Database configuration (loaded from environment variables)
DATABASE: dict = {
    "engine": "sqlite",  # Will be overridden by environment
    "name": "blog_platform.db",
    "host": "localhost",
    "port": 5432,
    "user": "",
    "password": "",
}

# Worker configuration
WORKERS: dict = {
    "email_notifications": {
        "enabled": True,
        "interval": 60,  # Check every 60 seconds
    },
    "content_indexer": {
        "enabled": True,
        "interval": 300,  # Re-index every 5 minutes
    },
}
```

#### `config/spoc.toml`

```toml
# SPOC Configuration File
# Defines environment-specific settings and app loading

[spoc]
mode = "development"  # Options: development, staging, production
debug = true

# Environment-specific apps
[spoc.apps]
# These apps are ONLY loaded in production
production = []

# These apps load in staging and production
staging = []

# These apps load only in development
development = []

# Additional plugins by environment
[spoc.plugins]
middleware = []
hooks = []
```

#### `config/.env.example`

```bash
# Development Environment Variables
# Copy this to .env and update with your values

# Application
SPOC_MODE=development
DEBUG=true

# Database
DB_ENGINE=sqlite
DB_NAME=blog_platform.db
DB_HOST=localhost
DB_PORT=5432
DB_USER=
DB_PASSWORD=

# Email
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=

# Workers
ENABLE_EMAIL_WORKER=true
ENABLE_INDEXER_WORKER=true
```

---

### 2. Framework Setup

#### `framework/components.py`

```python
"""
Shared component registry for the application.

This module defines the component types used across all apps
and provides decorator functions for consistent registration.
"""

from spoc import Components

# Initialize the component registry with all types
components = Components()

# Register component types
components.add_type("model")
components.add_type("view")
components.add_type("service")
components.add_type("worker")


# Convenience decorator functions
def model(cls):
    """Register a class as a model component."""
    return components.register("model")(cls)


def view(func):
    """Register a function as a view component."""
    return components.register("view")(func)


def service(cls):
    """Register a class as a service component."""
    return components.register("service")(cls)


def worker(cls):
    """Register a class as a worker component."""
    return components.register("worker")(cls)
```

#### `framework/database.py`

```python
"""
Database management utilities.

Provides a simple in-memory database simulation for the example.
In production, this would connect to a real database.
"""

from typing import Any, Dict, List


class Database:
    """Simple in-memory database for demonstration purposes."""

    def __init__(self):
        """Initialize the database with empty tables."""
        self._tables: Dict[str, List[Dict[str, Any]]] = {
            "users": [],
            "posts": [],
            "comments": [],
        }
        self._sequences: Dict[str, int] = {
            "users": 1,
            "posts": 1,
            "comments": 1,
        }

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert a record into a table.

        Args:
            table: Name of the table
            data: Record data to insert

        Returns:
            The ID of the inserted record
        """
        record_id = self._sequences[table]
        self._sequences[table] += 1

        record = {"id": record_id, **data}
        self._tables[table].append(record)
        return record_id

    def find_by_id(self, table: str, record_id: int) -> Dict[str, Any] | None:
        """
        Find a record by ID.

        Args:
            table: Name of the table
            record_id: ID of the record to find

        Returns:
            The record if found, None otherwise
        """
        for record in self._tables[table]:
            if record["id"] == record_id:
                return record
        return None

    def find_all(self, table: str) -> List[Dict[str, Any]]:
        """
        Get all records from a table.

        Args:
            table: Name of the table

        Returns:
            List of all records in the table
        """
        return self._tables[table].copy()

    def clear(self):
        """Clear all data from the database."""
        for table in self._tables:
            self._tables[table].clear()
            self._sequences[table] = 1


# Global database instance
db = Database()
```

---

### 3. Users App

#### `apps/users/__init__.py`

```python
"""
Users app initialization.

This app handles user authentication, profiles, and user management.
"""
```

#### `apps/users/models.py`

```python
"""
User models.

Defines the data structures for user-related entities.
"""

import dataclasses as dc
from datetime import datetime
from framework.components import model


@dc.dataclass
@model
class User:
    """
    User model representing a registered user.

    Attributes:
        id: Unique user identifier
        username: Unique username for login
        email: User's email address
        full_name: User's full name
        created_at: Timestamp when user was created
        is_active: Whether the user account is active
    """

    id: int
    username: str
    email: str
    full_name: str
    created_at: datetime
    is_active: bool = True

    def __str__(self) -> str:
        return f"User(id={self.id}, username={self.username})"


@dc.dataclass
@model
class UserProfile:
    """
    Extended user profile information.

    Attributes:
        user_id: Reference to the User
        bio: User biography
        avatar_url: URL to user's avatar image
        website: User's website URL
    """

    user_id: int
    bio: str = ""
    avatar_url: str = ""
    website: str = ""
```

#### `apps/users/services.py`

```python
"""
User services.

Business logic for user management operations.
"""

from datetime import datetime
from typing import Optional

from framework.components import service
from framework.database import db


@service
class UserService:
    """
    Service for managing user operations.

    Provides methods for user registration, authentication,
    and profile management.
    """

    def __init__(self):
        """Initialize the user service."""
        self.db = db

    def create_user(
        self,
        username: str,
        email: str,
        full_name: str,
    ) -> int:
        """
        Create a new user.

        Args:
            username: Unique username
            email: User's email address
            full_name: User's full name

        Returns:
            The ID of the created user
        """
        user_data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "created_at": datetime.now(),
            "is_active": True,
        }
        user_id = self.db.insert("users", user_data)
        print(f"  [UserService] Created user: {username} (ID: {user_id})")
        return user_id

    def get_user(self, user_id: int) -> Optional[dict]:
        """
        Get a user by ID.

        Args:
            user_id: The user's ID

        Returns:
            User data if found, None otherwise
        """
        return self.db.find_by_id("users", user_id)

    def list_users(self) -> list:
        """
        List all users.

        Returns:
            List of all users
        """
        return self.db.find_all("users")

    def authenticate(self, username: str) -> Optional[dict]:
        """
        Authenticate a user by username.

        Args:
            username: Username to authenticate

        Returns:
            User data if authenticated, None otherwise
        """
        users = self.db.find_all("users")
        for user in users:
            if user["username"] == username and user["is_active"]:
                return user
        return None
```

#### `apps/users/views.py`

```python
"""
User views.

HTTP request handlers for user-related endpoints.
"""

from typing import Any, Dict

from framework.components import view


@view
def register_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle user registration request.

    Args:
        data: Registration data containing username, email, full_name

    Returns:
        Response with user ID and status
    """
    # In a real app, this would validate input and call the service
    return {
        "action": "register_user",
        "status": "success",
        "data": data,
    }


@view
def login_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle user login request.

    Args:
        data: Login credentials

    Returns:
        Response with authentication token
    """
    return {
        "action": "login_user",
        "status": "success",
        "username": data.get("username"),
    }


@view
def get_profile(user_id: int) -> Dict[str, Any]:
    """
    Get user profile.

    Args:
        user_id: ID of the user

    Returns:
        User profile data
    """
    return {
        "action": "get_profile",
        "status": "success",
        "user_id": user_id,
    }
```

#### `apps/users/workers.py`

```python
"""
User workers.

Background tasks for user-related operations.
"""

import time
from framework.components import worker
from spoc.workers import ThreadWorker


@worker
class EmailNotificationWorker(ThreadWorker):
    """
    Background worker for sending email notifications.

    Periodically checks for pending notifications and sends emails.
    """

    def __init__(self):
        """Initialize the email notification worker."""
        super().__init__(name="EmailNotificationWorker", daemon=True)
        self.check_interval = 60  # Check every 60 seconds

    def setup(self) -> None:
        """Setup the worker (runs before main loop)."""
        print(f"  [{self.name}] Initializing email service...")
        self.context.email_queue = []
        self.context.sent_count = 0

    def main(self) -> None:
        """
        Main worker loop.

        Checks for pending emails and sends them.
        """
        print(f"  [{self.name}] Started monitoring email queue")

        while self.is_running:
            # Simulate checking for pending emails
            pending = len(self.context.email_queue)
            if pending > 0:
                print(f"  [{self.name}] Processing {pending} pending emails...")
                self.context.sent_count += pending
                self.context.email_queue.clear()

            # Wait before next check
            time.sleep(self.check_interval)

    def teardown(self) -> None:
        """Cleanup when worker stops."""
        print(
            f"  [{self.name}] Shutting down. "
            f"Total emails sent: {self.context.sent_count}"
        )

    def lifecycle(self, event_type: str, **data) -> None:
        """Handle lifecycle events."""
        if event_type == "startup":
            print(f"  [{self.name}] Lifecycle: Started")
        elif event_type == "shutdown":
            print(f"  [{self.name}] Lifecycle: Stopped")
        elif event_type == "error":
            print(f"  [{self.name}] Error: {data.get('exception')}")
```

---

### 4. Blog App

#### `apps/blog/__init__.py`

```python
"""
Blog app initialization.

This app handles blog posts, comments, and content management.
"""
```

#### `apps/blog/models.py`

```python
"""
Blog models.

Defines the data structures for blog-related entities.
"""

import dataclasses as dc
from datetime import datetime
from framework.components import model


@dc.dataclass
@model
class Post:
    """
    Blog post model.

    Attributes:
        id: Unique post identifier
        title: Post title
        content: Post content (markdown supported)
        author_id: ID of the user who created the post
        created_at: When the post was created
        updated_at: When the post was last updated
        published: Whether the post is published
        slug: URL-friendly version of the title
    """

    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime
    updated_at: datetime
    published: bool = False
    slug: str = ""

    def __str__(self) -> str:
        return f"Post(id={self.id}, title={self.title})"


@dc.dataclass
@model
class Comment:
    """
    Comment model for blog posts.

    Attributes:
        id: Unique comment identifier
        post_id: ID of the post being commented on
        author_id: ID of the user who wrote the comment
        text: Comment text
        created_at: When the comment was created
        approved: Whether the comment is approved for display
    """

    id: int
    post_id: int
    author_id: int
    text: str
    created_at: datetime
    approved: bool = False

    def __str__(self) -> str:
        return f"Comment(id={self.id}, post_id={self.post_id})"
```

#### `apps/blog/services.py`

```python
"""
Blog services.

Business logic for blog operations including post and comment management.
"""

from datetime import datetime
from typing import List, Optional

from framework.components import service
from framework.database import db


@service
class PostService:
    """
    Service for managing blog posts.

    Handles post creation, updates, publishing, and retrieval.
    """

    def __init__(self):
        """Initialize the post service."""
        self.db = db

    def create_post(
        self,
        title: str,
        content: str,
        author_id: int,
    ) -> int:
        """
        Create a new blog post.

        Args:
            title: Post title
            content: Post content
            author_id: ID of the author

        Returns:
            The ID of the created post
        """
        slug = title.lower().replace(" ", "-")
        post_data = {
            "title": title,
            "content": content,
            "author_id": author_id,
            "slug": slug,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "published": False,
        }
        post_id = self.db.insert("posts", post_data)
        print(f"  [PostService] Created post: {title} (ID: {post_id})")
        return post_id

    def publish_post(self, post_id: int) -> bool:
        """
        Publish a post.

        Args:
            post_id: ID of the post to publish

        Returns:
            True if successful, False otherwise
        """
        post = self.db.find_by_id("posts", post_id)
        if post:
            post["published"] = True
            post["updated_at"] = datetime.now()
            print(f"  [PostService] Published post ID: {post_id}")
            return True
        return False

    def get_post(self, post_id: int) -> Optional[dict]:
        """
        Get a post by ID.

        Args:
            post_id: The post's ID

        Returns:
            Post data if found, None otherwise
        """
        return self.db.find_by_id("posts", post_id)

    def list_posts(self, published_only: bool = False) -> List[dict]:
        """
        List all posts.

        Args:
            published_only: Whether to return only published posts

        Returns:
            List of posts
        """
        posts = self.db.find_all("posts")
        if published_only:
            return [p for p in posts if p.get("published", False)]
        return posts


@service
class CommentService:
    """
    Service for managing blog comments.

    Handles comment creation, moderation, and retrieval.
    """

    def __init__(self):
        """Initialize the comment service."""
        self.db = db

    def create_comment(
        self,
        post_id: int,
        author_id: int,
        text: str,
    ) -> int:
        """
        Create a new comment.

        Args:
            post_id: ID of the post being commented on
            author_id: ID of the comment author
            text: Comment text

        Returns:
            The ID of the created comment
        """
        comment_data = {
            "post_id": post_id,
            "author_id": author_id,
            "text": text,
            "created_at": datetime.now(),
            "approved": False,
        }
        comment_id = self.db.insert("comments", comment_data)
        print(f"  [CommentService] Created comment on post {post_id} (ID: {comment_id})")
        return comment_id

    def approve_comment(self, comment_id: int) -> bool:
        """
        Approve a comment for display.

        Args:
            comment_id: ID of the comment to approve

        Returns:
            True if successful, False otherwise
        """
        comment = self.db.find_by_id("comments", comment_id)
        if comment:
            comment["approved"] = True
            print(f"  [CommentService] Approved comment ID: {comment_id}")
            return True
        return False

    def get_comments_for_post(self, post_id: int) -> List[dict]:
        """
        Get all comments for a post.

        Args:
            post_id: ID of the post

        Returns:
            List of comments
        """
        comments = self.db.find_all("comments")
        return [c for c in comments if c["post_id"] == post_id]
```

#### `apps/blog/views.py`

```python
"""
Blog views.

HTTP request handlers for blog-related endpoints.
"""

from typing import Any, Dict

from framework.components import view


@view
def list_posts() -> Dict[str, Any]:
    """
    List all blog posts.

    Returns:
        Response with list of posts
    """
    return {
        "action": "list_posts",
        "status": "success",
    }


@view
def create_post(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new blog post.

    Args:
        data: Post data including title, content, author_id

    Returns:
        Response with created post ID
    """
    return {
        "action": "create_post",
        "status": "success",
        "data": data,
    }


@view
def get_post(post_id: int) -> Dict[str, Any]:
    """
    Get a specific blog post.

    Args:
        post_id: ID of the post to retrieve

    Returns:
        Response with post data
    """
    return {
        "action": "get_post",
        "status": "success",
        "post_id": post_id,
    }


@view
def add_comment(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a comment to a post.

    Args:
        data: Comment data including post_id, author_id, text

    Returns:
        Response with created comment ID
    """
    return {
        "action": "add_comment",
        "status": "success",
        "data": data,
    }
```

#### `apps/blog/workers.py`

```python
"""
Blog workers.

Background tasks for blog-related operations.
"""

import time
from framework.components import worker
from spoc.workers import ProcessWorker


@worker
class ContentIndexerWorker(ProcessWorker):
    """
    Background worker for indexing blog content.

    Periodically re-indexes blog posts for search functionality.
    This runs in a separate process to avoid blocking the main application.
    """

    def __init__(self):
        """Initialize the content indexer worker."""
        super().__init__(name="ContentIndexerWorker", daemon=True)
        self.index_interval = 300  # Re-index every 5 minutes

    def setup(self) -> None:
        """Setup the worker (runs before main loop)."""
        print(f"  [{self.name}] Initializing search index...")
        self.context.indexed_posts = 0
        self.context.last_index_time = None

    def main(self) -> None:
        """
        Main worker loop.

        Periodically re-indexes all blog posts for search.
        """
        print(f"  [{self.name}] Started content indexing")

        while self.is_running:
            # Simulate indexing posts
            print(f"  [{self.name}] Re-indexing content...")
            self.context.indexed_posts += 10  # Simulated
            self.context.last_index_time = time.time()

            # Wait before next index
            time.sleep(self.index_interval)

    def teardown(self) -> None:
        """Cleanup when worker stops."""
        print(
            f"  [{self.name}] Shutting down. "
            f"Total posts indexed: {self.context.indexed_posts}"
        )

    def lifecycle(self, event_type: str, **data) -> None:
        """Handle lifecycle events."""
        if event_type == "startup":
            print(f"  [{self.name}] Lifecycle: Started")
        elif event_type == "shutdown":
            print(f"  [{self.name}] Lifecycle: Stopped")
        elif event_type == "error":
            print(f"  [{self.name}] Error: {data.get('exception')}")
```

---

### 5. Main Application

#### `main.py`

```python
"""
Main application entry point.

This module bootstraps the SPOC framework, initializes all apps,
sets up lifecycle hooks, and starts background workers.
"""

from pathlib import Path
import time

from spoc import Framework, Schema, Hook
from spoc.workers import Server
from config import settings
from framework.database import db


def init_database(module) -> None:
    """
    Initialize the database when models are loaded.

    This hook is called when model modules are loaded, allowing
    database setup before any data operations occur.

    Args:
        module: The module being loaded
    """
    print(f"  [Database] Initializing tables for: {module.__name__}")
    # In a real app, create tables, run migrations, etc.


def close_database(module) -> None:
    """
    Close database connections when shutting down.

    This hook is called when the application is shutting down,
    ensuring proper cleanup of database resources.

    Args:
        module: The module being unloaded
    """
    print(f"  [Database] Closing connections for: {module.__name__}")
    # In a real app, close connections, save state, etc.


def init_services(module) -> None:
    """
    Initialize services when loaded.

    Args:
        module: The service module being loaded
    """
    print(f"  [Services] Initializing: {module.__name__}")


# Define the application schema
schema = Schema(
    # Modules to load from each app (in order)
    modules=["models", "views", "services", "workers"],
    # Module dependencies (ensure models load before views and services)
    dependencies={
        "views": ["models"],
        "services": ["models"],
        "workers": ["models", "services"],
    },
    # Lifecycle hooks for module initialization and cleanup
    hooks={
        "models": Hook(
            startup=init_database,
            shutdown=close_database,
        ),
        "services": Hook(
            startup=init_services,
        ),
        "views": Hook(
            startup=lambda m: print(f"  [Views] Loaded: {m.__name__}"),
        ),
        "workers": Hook(
            startup=lambda m: print(f"  [Workers] Registered: {m.__name__}"),
        ),
    },
)

# Create the framework instance
framework = Framework(
    base_dir=settings.BASE_DIR,
    schema=schema,
    echo=False,
    mode="strict",
)


def demonstrate_app_interaction():
    """
    Demonstrate how apps interact through the framework.

    Shows dependency injection, service usage, and cross-app communication.
    """
    print("\n" + "=" * 60)
    print("DEMONSTRATING APP INTERACTION")
    print("=" * 60)

    # Get services from the framework
    UserService = framework.get_component("services", "users.UserService")
    PostService = framework.get_component("services", "blog.PostService")
    CommentService = framework.get_component("services", "blog.CommentService")

    if not all([UserService, PostService, CommentService]):
        print("  [ERROR] Could not load all required services")
        return

    # Instantiate services
    user_service = UserService()
    post_service = PostService()
    comment_service = CommentService()

    print("\n--- Creating Users ---")
    user1_id = user_service.create_user(
        username="alice",
        email="alice@example.com",
        full_name="Alice Johnson",
    )
    user2_id = user_service.create_user(
        username="bob",
        email="bob@example.com",
        full_name="Bob Smith",
    )

    print("\n--- Creating Blog Posts ---")
    post1_id = post_service.create_post(
        title="Getting Started with SPOC",
        content="SPOC is a powerful framework for building modular applications...",
        author_id=user1_id,
    )
    post2_id = post_service.create_post(
        title="Advanced SPOC Patterns",
        content="Learn about advanced patterns and best practices...",
        author_id=user1_id,
    )

    print("\n--- Publishing Posts ---")
    post_service.publish_post(post1_id)
    post_service.publish_post(post2_id)

    print("\n--- Adding Comments ---")
    comment1_id = comment_service.create_comment(
        post_id=post1_id,
        author_id=user2_id,
        text="Great article! Very helpful.",
    )
    comment2_id = comment_service.create_comment(
        post_id=post1_id,
        author_id=user1_id,
        text="Thank you for the feedback!",
    )

    print("\n--- Approving Comments ---")
    comment_service.approve_comment(comment1_id)
    comment_service.approve_comment(comment2_id)

    print("\n--- Summary ---")
    print(f"  Total users: {len(user_service.list_users())}")
    print(f"  Total posts: {len(post_service.list_posts())}")
    print(f"  Published posts: {len(post_service.list_posts(published_only=True))}")
    print(f"  Comments on post 1: {len(comment_service.get_comments_for_post(post1_id))}")


def demonstrate_components():
    """Display all registered components."""
    print("\n" + "=" * 60)
    print("REGISTERED COMPONENTS")
    print("=" * 60)

    # Display models
    print("\n--- Models ---")
    if hasattr(framework.components, "models"):
        for name, model in framework.components.models.items():
            print(f"  • {name}: {model}")

    # Display views
    print("\n--- Views ---")
    if hasattr(framework.components, "views"):
        for name, view in framework.components.views.items():
            print(f"  • {name}: {view}")

    # Display services
    print("\n--- Services ---")
    if hasattr(framework.components, "services"):
        for name, service in framework.components.services.items():
            print(f"  • {name}: {service}")

    # Display workers
    print("\n--- Workers ---")
    if hasattr(framework.components, "workers"):
        for name, worker in framework.components.workers.items():
            print(f"  • {name}: {worker}")


def start_background_workers():
    """
    Start background workers using the Server.

    Demonstrates how to initialize and manage multiple workers
    that run concurrently with the main application.
    """
    print("\n" + "=" * 60)
    print("STARTING BACKGROUND WORKERS")
    print("=" * 60 + "\n")

    # Create worker server
    server = Server(name="BlogPlatformServer")

    # Get worker classes from framework
    EmailWorker = framework.get_component("workers", "users.EmailNotificationWorker")
    IndexWorker = framework.get_component("workers", "blog.ContentIndexerWorker")

    if EmailWorker:
        email_worker = EmailWorker()
        server.add_worker(email_worker)
        print(f"  • Added {email_worker.name}")

    if IndexWorker:
        index_worker = IndexWorker()
        server.add_worker(index_worker)
        print(f"  • Added {index_worker.name}")

    # Start all workers
    print("\n  Starting workers...\n")
    server.start()

    # Let workers run for a bit
    print("  Workers are running (will stop in 5 seconds)...\n")
    time.sleep(5)

    # Stop workers
    print("\n  Stopping workers...\n")
    server.stop()
    server.join_all(timeout=2)


def main():
    """
    Main application entry point.

    Orchestrates the entire application lifecycle including:
    1. Framework initialization
    2. Component registration and display
    3. Cross-app interaction demonstration
    4. Background worker management
    5. Graceful shutdown
    """
    print("\n" + "=" * 60)
    print("BLOG PLATFORM - SPOC APPLICATION")
    print("=" * 60)
    print(f"\nInstalled apps: {framework.installed_apps}")

    # Display all registered components
    demonstrate_components()

    # Demonstrate app interaction
    demonstrate_app_interaction()

    # Start and manage background workers
    start_background_workers()

    # Cleanup
    print("\n" + "=" * 60)
    print("SHUTTING DOWN APPLICATION")
    print("=" * 60 + "\n")

    # Clear database
    db.clear()

    # Shutdown framework
    framework.shutdown()

    print("\n" + "=" * 60)
    print("APPLICATION STOPPED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
```

---

## Running the Application

### 1. Install Dependencies

Create `requirements.txt`:

```txt
spoc>=0.2.0
```

Install:

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Copy the example environment file:

```bash
cp config/.env.example config/.env
```

Edit `config/.env` with your settings.

### 3. Run the Application

```bash
python main.py
```

---

## Expected Output

```
============================================================
BLOG PLATFORM - SPOC APPLICATION
============================================================

Installed apps: ['users', 'blog']

============================================================
REGISTERED COMPONENTS
============================================================

--- Models ---
  • users.User: <class 'users.models.User'>
  • users.UserProfile: <class 'users.models.UserProfile'>
  • blog.Post: <class 'blog.models.Post'>
  • blog.Comment: <class 'blog.models.Comment'>

--- Views ---
  • users.register_user: <function register_user at 0x...>
  • users.login_user: <function login_user at 0x...>
  • users.get_profile: <function get_profile at 0x...>
  • blog.list_posts: <function list_posts at 0x...>
  • blog.create_post: <function create_post at 0x...>
  • blog.get_post: <function get_post at 0x...>
  • blog.add_comment: <function add_comment at 0x...>

--- Services ---
  • users.UserService: <class 'users.services.UserService'>
  • blog.PostService: <class 'blog.services.PostService'>
  • blog.CommentService: <class 'blog.services.CommentService'>

--- Workers ---
  • users.EmailNotificationWorker: <class 'users.workers.EmailNotificationWorker'>
  • blog.ContentIndexerWorker: <class 'blog.workers.ContentIndexerWorker'>

============================================================
DEMONSTRATING APP INTERACTION
============================================================

--- Creating Users ---
  [UserService] Created user: alice (ID: 1)
  [UserService] Created user: bob (ID: 2)

--- Creating Blog Posts ---
  [PostService] Created post: Getting Started with SPOC (ID: 1)
  [PostService] Created post: Advanced SPOC Patterns (ID: 2)

--- Publishing Posts ---
  [PostService] Published post ID: 1
  [PostService] Published post ID: 2

--- Adding Comments ---
  [CommentService] Created comment on post 1 (ID: 1)
  [CommentService] Created comment on post 1 (ID: 2)

--- Approving Comments ---
  [CommentService] Approved comment ID: 1
  [CommentService] Approved comment ID: 2

--- Summary ---
  Total users: 2
  Total posts: 2
  Published posts: 2
  Comments on post 1: 2

============================================================
STARTING BACKGROUND WORKERS
============================================================

  • Added EmailNotificationWorker
  • Added ContentIndexerWorker

  Starting workers...

  [EmailNotificationWorker] Lifecycle: Started
  [EmailNotificationWorker] Initializing email service...
  [EmailNotificationWorker] Started monitoring email queue
  [ContentIndexerWorker] Lifecycle: Started
  [ContentIndexerWorker] Initializing search index...
  [ContentIndexerWorker] Started content indexing

  Workers are running (will stop in 5 seconds)...

  Stopping workers...

  [EmailNotificationWorker] Shutting down. Total emails sent: 0
  [EmailNotificationWorker] Lifecycle: Stopped
  [ContentIndexerWorker] Shutting down. Total posts indexed: 0
  [ContentIndexerWorker] Lifecycle: Stopped

============================================================
SHUTTING DOWN APPLICATION
============================================================

============================================================
APPLICATION STOPPED
============================================================
```

---

## Key Concepts Demonstrated

### 1. Multi-App Architecture

The example shows two independent apps (users, blog) that can be developed separately but work together through the framework:

```python
INSTALLED_APPS: list = [
    "users",  # User management
    "blog",   # Blog functionality
]
```

### 2. Component Registration

Each app registers its components using the shared registry:

```python
from framework.components import model, service, view, worker

@model
class User:
    pass

@service
class UserService:
    pass
```

### 3. Dependency Resolution

The schema defines how modules depend on each other:

```python
dependencies={
    "views": ["models"],
    "services": ["models"],
    "workers": ["models", "services"],
}
```

This ensures models are loaded before views and services, preventing import errors.

### 4. Lifecycle Hooks

Hooks execute at specific points in the application lifecycle:

```python
hooks={
    "models": Hook(
        startup=init_database,
        shutdown=close_database,
    ),
}
```

### 5. Cross-App Communication

Apps interact through the framework's component registry:

```python
# Get services from different apps
UserService = framework.get_component("services", "users.UserService")
PostService = framework.get_component("services", "blog.PostService")

# Use them together
user_id = user_service.create_user(...)
post_id = post_service.create_post(author_id=user_id, ...)
```

### 6. Background Workers

Workers run concurrently using threads or processes:

```python
# Thread worker for I/O-bound tasks
class EmailNotificationWorker(ThreadWorker):
    pass

# Process worker for CPU-bound tasks
class ContentIndexerWorker(ProcessWorker):
    pass
```

### 7. Environment Configuration

Settings can be customized per environment:

```toml
[spoc]
mode = "development"

[spoc.apps]
production = []
development = []
```

---

## Extending the Example

### Add More Apps

Create new apps following the same structure:

```
apps/
├── analytics/      # Analytics and reporting
├── notifications/  # Push notifications
└── search/        # Full-text search
```

### Add Custom Components

Define new component types:

```python
from framework.components import components

components.add_type("middleware")
components.add_type("command")
```

### Add Plugins

Create plugins for cross-cutting concerns:

```python
PLUGINS: dict = {
    "middleware": [
        "framework.middleware.LoggingMiddleware",
        "framework.middleware.AuthMiddleware",
    ],
}
```

### Use Real Database

Replace the in-memory database with SQLAlchemy, Django ORM, or another database library:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def init_database(module):
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    # Create tables, etc.
```

---

## Best Practices

### 1. Separation of Concerns

Keep each app focused on a single domain:

- `users` handles authentication and user management
- `blog` handles content creation and display
- Keep cross-cutting concerns in the `framework` package

### 2. Component Naming

Use consistent naming conventions:

- Models: `User`, `Post`, `Comment`
- Services: `UserService`, `PostService`
- Views: `list_posts`, `create_post`
- Workers: `EmailNotificationWorker`

### 3. Dependency Injection

Access framework components through dependency injection:

```python
class PostService:
    def __init__(self):
        # Get dependencies from the framework
        self.user_service = framework.get_component(
            "services", "users.UserService"
        )()
```

### 4. Error Handling

Implement proper error handling in services and workers:

```python
def lifecycle(self, event_type: str, **data) -> None:
    if event_type == "error":
        logger.error(f"Worker error: {data.get('exception')}")
```

### 5. Testing

Test components in isolation:

```python
def test_user_service():
    service = UserService()
    user_id = service.create_user("test", "test@example.com", "Test User")
    assert user_id > 0
```

---

## Troubleshooting

### Components Not Found

**Problem**: `framework.get_component()` returns `None`.

**Solution**: Ensure:
- The module is listed in `schema.modules`
- The component is decorated with the correct decorator
- The app is in `INSTALLED_APPS`

### Circular Dependencies

**Problem**: `CircularDependencyError` during startup.

**Solution**: Review your `schema.dependencies` and restructure to remove cycles.

### Workers Not Starting

**Problem**: Workers don't run or stop immediately.

**Solution**: Check:
- Workers inherit from `ThreadWorker` or `ProcessWorker`
- The `main()` method has a loop that checks `self.is_running`
- The worker is added to the server before calling `start()`

### Module Import Errors

**Problem**: `ModuleNotFoundError` when loading apps.

**Solution**: Ensure:
- Each app directory has `__init__.py`
- Module names match file names
- Dependencies are declared in the schema

---

## Summary

This example demonstrates a production-ready SPOC application with:

- **Two apps** (users, blog) with proper separation of concerns
- **Multiple component types** (models, views, services, workers)
- **Cross-app dependencies** through the framework registry
- **Lifecycle hooks** for database initialization
- **Background workers** using threads and processes
- **Environment configuration** for different deployment scenarios

You can use this as a starting template for your own SPOC applications, extending it with additional apps, components, and functionality as needed.

---

## Next Steps

- Read the [Framework API](../api/framework.md) for advanced features
- Explore [Lifecycle Hooks](../advanced/lifecycle.md) for more hook patterns
- Check out [Workers](../advanced/workers.md) for worker best practices
- Review [Configuration](../getting-started/configuration.md) for environment management
