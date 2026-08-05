"""
Tests for the module loader (spec: framework-lifecycle).

The loader is kind-blind: it carries a kind label it never interprets. Its contract is
dependency order, the absent-versus-broken distinction, and lifecycle dispatch.

Replaces the old importer tests. Coverage of the module cache API (`has`, `get`, `clear`,
`clear_all`, `unload_all`, `keys`), the configurable hook-function names, and the
wildcard-pattern hook engine went with the API itself — see the change proposal.
"""

import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

from spoc.core.exceptions import (
    AppNotFoundError,
    CircularDependencyError,
    MissingModuleError,
    SpocError,
    UnresolvedReferenceError,
)
from spoc.core.loader import LoadedModule, Loader


def fake(name: str, kind: str = "models", **attrs) -> LoadedModule:
    """A LoadedModule around a synthetic module, without touching the filesystem."""
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return LoadedModule(name=name, module=module, kind=kind)


@pytest.fixture
def loader():
    return Loader()


@pytest.fixture
def app_tree(tmp_path):
    """A two-app project on the import path: `full` has both kinds, `partial` one."""
    sys.path.insert(0, str(tmp_path))
    for app, modules in (("full", ("models", "views")), ("partial", ("models",))):
        pkg = tmp_path / app
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        for kind in modules:
            (pkg / f"{kind}.py").write_text("value = 1\n")
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "__init__.py").write_text("")
    (tmp_path / "broken" / "models.py").write_text("import no_such_dependency\n")
    try:
        yield tmp_path
    finally:
        sys.path.remove(str(tmp_path))


class TestRegistration:
    def test_registers_and_returns_the_module(self, loader, app_tree):
        module = loader.register("full.models", kind="models", app="full")
        assert module is sys.modules["full.models"]
        assert len(loader) == 1

    def test_dependency_edges_recorded(self, loader, app_tree):
        loader.register("full.models", kind="models", app="full")
        loader.register(
            "full.views", kind="views", app="full", dependencies=("full.models",)
        )
        assert "full.models" in loader._graph["full.views"]

    def test_edges_recorded_before_the_dependency_is_loaded(self, loader, app_tree):
        """Registration order must not silently drop an edge."""
        loader.register(
            "full.views", kind="views", app="full", dependencies=("full.models",)
        )
        loader.register("full.models", kind="models", app="full")
        assert [e.name for e in loader.ordered()] == ["full.models", "full.views"]

    def test_registering_twice_is_idempotent(self, loader, app_tree):
        first = loader.register("full.models", kind="models", app="full")
        second = loader.register("full.models", kind="models", app="full")
        assert first is second
        assert len(loader) == 1


class TestAbsentVersusBroken:
    def test_absent_required_module_raises(self, loader, app_tree):
        with pytest.raises(MissingModuleError) as exc:
            loader.register("partial.views", kind="views", app="partial")
        message = str(exc.value)
        assert "partial" in message and "views" in message

    def test_absent_optional_module_is_skipped(self, loader, app_tree):
        result = loader.register(
            "partial.views", kind="views", app="partial", required=False
        )
        assert result is None
        assert len(loader) == 0

    def test_broken_module_raises_even_when_optional(self, loader, app_tree):
        """Present-and-broken is always an error — the author wrote something wrong."""
        with pytest.raises(ModuleNotFoundError) as exc:
            loader.register(
                "broken.models", kind="models", app="broken", required=False
            )
        assert exc.value.name == "no_such_dependency"

    def test_absent_app_package_is_a_named_refusal(self, loader, app_tree):
        """A declared app that does not exist raises the kernel's error, not a raw one."""
        with pytest.raises(AppNotFoundError) as exc:
            loader.register("ghost.models", kind="models", app="ghost")
        assert exc.value.module_name == "ghost"

    def test_absent_app_package_fails_even_for_an_optional_kind(self, loader, app_tree):
        """`required` lets an existing app omit a kind; it cannot excuse a missing app."""
        with pytest.raises(AppNotFoundError):
            loader.register("ghost.models", kind="models", app="ghost", required=False)


class TestOrdering:
    def test_dependency_order_and_reverse_teardown(self, loader):
        events: list[str] = []
        for name in ("a", "b", "c"):
            entry = fake(
                name,
                initialize=lambda n=name: events.append(f"up:{n}"),
                teardown=lambda n=name: events.append(f"down:{n}"),
            )
            loader._modules[name] = entry
            loader._graph.setdefault(name, set())
        loader._graph["b"].add("a")
        loader._graph["c"].add("b")

        loader.initialize({}, lambda entry: ())
        assert events == ["up:a", "up:b", "up:c"]

        events.clear()
        loader.shutdown({}, lambda entry: ())
        assert events == ["down:c", "down:b", "down:a"]

    def test_circular_dependency_detected(self, loader):
        for name in ("one", "two"):
            loader._modules[name] = fake(name)
            loader._graph.setdefault(name, set())
        loader._graph["one"].add("two")
        loader._graph["two"].add("one")

        with pytest.raises(CircularDependencyError):
            loader.ordered()

    def test_modules_without_lifecycle_functions_are_fine(self, loader):
        loader._modules["plain"] = fake("plain")
        loader._graph["plain"] = set()
        loader.initialize({}, lambda entry: ())
        loader.shutdown({}, lambda entry: ())


class TestLifecycleHooks:
    def test_hooks_dispatch_by_kind(self, loader):
        seen: list[tuple[str, str]] = []
        loader._modules["blog.models"] = fake("blog.models", kind="models")
        loader._modules["blog.views"] = fake("blog.views", kind="views")
        loader._graph = {"blog.models": set(), "blog.views": set()}

        hooks = {
            "models": (
                lambda objs: seen.append(("up", "models")),
                lambda objs: seen.append(("down", "models")),
            )
        }
        loader.initialize(hooks, lambda entry: ())
        loader.shutdown(hooks, lambda entry: ())

        # only the `models` kind has hooks; `views` is silently unhooked
        assert seen == [("up", "models"), ("down", "models")]

    def test_hook_receives_the_module_components(self, loader):
        received: list[tuple] = []
        loader._modules["blog.models"] = fake("blog.models", kind="models")
        loader._graph = {"blog.models": set()}
        marker = object()

        loader.initialize(
            {"models": (lambda objs: received.append(objs), None)},
            lambda entry: (marker,),
        )
        assert received == [(marker,)]

    def test_app_initialize_error_propagates_unwrapped(self, loader):
        """The error doctrine: app-authored failures are never the kernel's to wrap."""

        def boom():
            raise RuntimeError("Initialization failed")

        loader._modules["bad"] = fake("bad", initialize=boom)
        loader._graph = {"bad": set()}

        with pytest.raises(RuntimeError, match="Initialization failed") as excinfo:
            loader.initialize({}, lambda entry: ())
        assert type(excinfo.value) is RuntimeError
        assert not isinstance(excinfo.value.__context__, SpocError)

    def test_shutdown_hook_error_propagates_unwrapped(self, loader):
        entry = fake("blog.models", kind="models")
        entry.initialized = True
        loader._modules["blog.models"] = entry
        loader._graph = {"blog.models": set()}

        def boom(objs):
            raise KeyError("shutdown boom")

        with pytest.raises(KeyError, match="shutdown boom") as excinfo:
            loader.shutdown({"models": (None, boom)}, lambda entry: ())
        assert type(excinfo.value) is KeyError


class TestLoadFromUri:
    @pytest.mark.parametrize(
        "uri,expected",
        [
            ("invalid", UnresolvedReferenceError),
            ("invalid.module.attr.extra", AppNotFoundError),
            ("os.nonexistent_attr", UnresolvedReferenceError),
            # Empty segments: importlib answers these with its own ValueError or
            # TypeError, which must never be what a caller sees.
            (".attr", UnresolvedReferenceError),
            ("..module.attr", UnresolvedReferenceError),
            ("package..module.attr", UnresolvedReferenceError),
            ("package.module.", UnresolvedReferenceError),
            (".", UnresolvedReferenceError),
        ],
    )
    def test_errors(self, loader, uri, expected):
        """Every reference failure is a named kernel refusal, not a raw exception."""
        with pytest.raises(expected):
            loader.load_from_uri(uri)

    def test_loads_functions_and_classes(self, loader):
        assert loader.load_from_uri("os.path.join") is os.path.join
        assert loader.load_from_uri("builtins.ValueError") is ValueError

    def test_broken_module_is_not_reported_as_absent(self, loader, app_tree):
        """A plugin module that exists but fails to import keeps its own error."""
        with pytest.raises(ModuleNotFoundError) as exc:
            loader.load_from_uri("broken.models.value")
        assert exc.value.name == "no_such_dependency"
        assert not isinstance(exc.value, AppNotFoundError)

    def test_loads_from_a_file_on_disk(self, loader):
        with tempfile.TemporaryDirectory() as temp_dir:
            sys.path.insert(0, temp_dir)
            try:
                (Path(temp_dir) / "functions.py").write_text(
                    "def hello(name):\n"
                    '    return f"Hello, {name}!"\n'
                    "\n"
                    "class Greeter:\n"
                    "    def greet(self, name):\n"
                    '        return f"Greetings, {name}!"\n'
                )
                assert loader.load_from_uri("functions.hello")("World") == (
                    "Hello, World!"
                )
                greeter = loader.load_from_uri("functions.Greeter")()
                assert greeter.greet("User") == "Greetings, User!"
            finally:
                sys.path.remove(temp_dir)
                sys.modules.pop("functions", None)


class TestRemovedApi:
    @pytest.mark.parametrize(
        "gone",
        [
            "has",
            "get",
            "clear",
            "clear_all",
            "unload_all",
            "keys",
            "startup",
            "register_hook",
            "simple_regex",
            "module_hooks",
            "on_startup",
            "on_shutdown",
        ],
    )
    def test_cache_and_pattern_hook_api_is_absent(self, loader, gone):
        assert not hasattr(loader, gone), gone
