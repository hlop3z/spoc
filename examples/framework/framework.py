# Standard Library
import functools
import logging
from typing import Any

# Project
from config import settings

from spoc import Components, Framework, Hook, Schema

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s(%(levelname)s) - %(message)s",
)

logger = logging.getLogger("spoc")

# ------------------------------------------------------------------------------
# Components — the declared, closed kind set (must match Schema.modules)
# ------------------------------------------------------------------------------
components = Components("models", "views")


def model(obj: Any = None, *, name: str | None = None):
    """Model decorator. Pass name= when the class name isn't snake_case."""
    if obj is None:
        return functools.partial(model, name=name)
    return components.register("models", obj, name=name)


def view(obj: Any = None, *, name: str | None = None):
    """View decorator — plain functions usually conform already."""
    if obj is None:
        return functools.partial(view, name=name)
    return components.register("views", obj, name=name)


# ------------------------------------------------------------------------------
# Schema — modules are the kind set; dependencies order the loading
# ------------------------------------------------------------------------------
SCHEMA = Schema(
    modules=["models", "views"],
    dependencies={"views": ["models"]},
    hooks={
        "models": Hook(
            startup=lambda m: logger.info("Init models: %s", m),
            shutdown=lambda m: logger.info("Tear down models: %s", m),
        ),
        "views": Hook(
            startup=lambda m: logger.info("Init views: %s", m),
            shutdown=lambda m: logger.info("Tear down views: %s", m),
        ),
    },
)

# ------------------------------------------------------------------------------
# Framework — the composition root; owns registry, importer, and hooks
# ------------------------------------------------------------------------------
framework = Framework(settings.BASE_DIR, SCHEMA, mode="strict")
