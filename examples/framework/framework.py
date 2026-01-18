# Standard Library
import functools
import logging
from pprint import pprint

from types import SimpleNamespace
from typing import Any

# Project
from config import settings

from spoc import Components, Framework, Hook, Schema, SingletonMeta
from spoc.types import Config

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s(%(levelname)s) – %(message)s",
)

logger = logging.getLogger("spoc")

# ------------------------------------------------------------------------------
# Components
# ------------------------------------------------------------------------------
components: Components = Components()
components.add_type("models")


def model(obj: Any = None, *, example: bool = False):
    """Model Decorator"""
    if obj is None:
        return functools.partial(model, example=example)

    # Real Wrapper
    components.register("models", obj, config={"config": "bar"})

    # Return Modified Class
    return obj


# ------------------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------------------
def init_models(m):
    logger.info("Init models: %s", m)


SCHEMA = Schema(
    modules=["models", "views"],
    dependencies={"views": ["models"]},
    hooks={
        "models": Hook(
            startup=init_models,
            shutdown=lambda m: logger.info("Tear down models: %s", m),
        ),
        "views": Hook(
            startup=lambda m: logger.info("Init views: %s", m),
            shutdown=lambda m: logger.info("Tear down views: %s", m),
        ),
    },
)

# ------------------------------------------------------------------------------
# Framework
# ------------------------------------------------------------------------------
framework = Framework(settings.BASE_DIR, SCHEMA, mode="strict")  # loose


class Base:
    root: Framework

    @classmethod
    def get_component(cls, kind: str, name: str) -> Any:
        return cls.root.get_component(kind, name)

    @classmethod
    def get_components(cls, kind: str) -> list[Any]:
        return cls.root.components.__dict__.get(kind, []).values()

    @classmethod
    def shutdown(cls) -> None:
        cls.root.shutdown()

    @classmethod
    def config(cls) -> Config:
        return cls.root.config


class App(Base, metaclass=SingletonMeta):
    root = framework

    def __init__(
        self,
    ):
        self.context = SimpleNamespace()
        self.base_dir = settings.BASE_DIR

    def startup(self):
        print("Installed Apps", self.root.installed_apps)
        print(SCHEMA.modules)
        # pprint(self.root.config.project)
        pprint(self.root.config.environment)
        # pprint(self.root.components.models.values())
