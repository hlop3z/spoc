"""The deprecation signal required by the release policy.

Both paths are tested on every interpreter: the stdlib decorator when it exists,
and the 3.12 fallback always — a fallback exercised only on the one version CI
might not run is a fallback nobody has checked.
"""

from __future__ import annotations

import inspect
import sys
import warnings

import pytest

from spoc.core.deprecation import (
    _fallback_deprecated,
    deprecated,
    deprecated_alias,
)

MESSAGE = "spoc.old_name is deprecated; use spoc.new_name instead"

IMPLEMENTATIONS = [pytest.param(_fallback_deprecated, id="fallback")]
if sys.version_info >= (3, 13):
    IMPLEMENTATIONS.append(pytest.param(deprecated, id="stdlib"))


@pytest.fixture(params=IMPLEMENTATIONS)
def mark(request):
    """Each implementation of PEP 702 available on this interpreter."""
    return request.param


def test_deprecated_function_still_works(mark):
    @mark(MESSAGE)
    def add(a, b):
        return a + b

    with pytest.warns(DeprecationWarning):
        assert add(2, 3) == 5


def test_function_warning_names_element_and_replacement(mark):
    @mark(MESSAGE)
    def old():
        return None

    with pytest.warns(DeprecationWarning, match="use spoc.new_name instead") as caught:
        old()
    assert "spoc.old_name" in str(caught[0].message)


def test_deprecated_class_still_constructs(mark):
    @mark(MESSAGE)
    class Old:
        def __init__(self, value):
            self.value = value

    with pytest.warns(DeprecationWarning):
        assert Old(7).value == 7


def test_class_without_init_still_constructs(mark):
    @mark(MESSAGE)
    class Bare:
        pass

    with pytest.warns(DeprecationWarning):
        assert isinstance(Bare(), Bare)


def test_subclass_of_deprecated_class_constructs_and_warns(mark):
    """Rebinding ``__new__`` must not break inheritance: deriving from and
    using a deprecated class warns, and the subclass gets *itself* back.

    Where the warning fires is implementation detail, deliberately untested:
    the stdlib decorator warns at subclass *creation* (``__init_subclass__``),
    the 3.12 fallback at *instantiation*. Both are one warning for the same
    act, and the fallback deletes itself when the floor reaches 3.13.
    """

    @mark(MESSAGE)
    class Old:
        def __init__(self, value):
            self.value = value

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        class Sub(Old):
            pass

        instance = Sub(7)

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    assert type(instance) is Sub
    assert instance.value == 7


def test_class_with_custom_new_still_constructs(mark):
    """A class allocating through its own ``__new__`` keeps that path intact,
    arguments and all."""

    @mark(MESSAGE)
    class Custom:
        via_new: bool = False

        def __new__(cls, *args, **kwargs):
            instance = super().__new__(cls)
            instance.via_new = True
            return instance

        def __init__(self, value, *, flag=False):
            self.value = value
            self.flag = flag

    with pytest.warns(DeprecationWarning):
        instance = Custom(7, flag=True)

    assert instance.via_new is True
    assert instance.value == 7 and instance.flag is True


def test_double_decoration_still_constructs_and_warns(mark):
    """Decorating twice chains the patched allocators. Nothing legislates how
    many warnings that emits — only that construction survives, at least one
    warning fires, and the outer message wins ``__deprecated__``."""

    @mark(MESSAGE)
    @mark("an earlier message")
    class Twice:
        def __init__(self, value):
            self.value = value

    with pytest.warns(DeprecationWarning) as caught:
        assert Twice(7).value == 7

    assert len(caught) >= 1
    assert Twice.__deprecated__ == MESSAGE


def test_mark_is_visible_without_calling(mark):
    """`__deprecated__` is what a type checker and the docs projection read."""

    @mark(MESSAGE)
    def old():
        return None

    assert old.__deprecated__ == MESSAGE


def test_warning_is_suppressible(mark):
    """The policy promises a consumer can silence it."""

    @mark(MESSAGE)
    def old():
        return "value"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert old() == "value"


def test_warning_is_escalatable(mark):
    """...and can be turned into an error, which is how a project bans them."""

    @mark(MESSAGE)
    def old():
        return None

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        with pytest.raises(DeprecationWarning):
            old()


def test_category_none_marks_without_warning(mark):
    """PEP 702: `category=None` records the deprecation but stays silent."""

    @mark(MESSAGE, category=None)
    def old():
        return "value"

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert old() == "value"
    assert old.__deprecated__ == MESSAGE


def test_function_metadata_survives(mark):
    @mark(MESSAGE)
    def documented(a, b):
        """A docstring that must not be lost."""
        return a + b

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "A docstring that must not be lost."


def test_the_exported_decorator_is_the_stdlib_one_when_available():
    """On 3.13+ nothing hand-written should be in the path."""
    if sys.version_info >= (3, 13):
        assert deprecated is warnings.deprecated
    else:  # pragma: no cover - only on 3.12
        assert deprecated is _fallback_deprecated


def test_alias_warns_while_the_definition_stays_silent(monkeypatch, mark):
    """The withdrawn spelling warns; the spelling being recommended does not.

    Both halves matter. Without the second, the migration the message names
    could itself be deprecated and no test would notice.
    """
    monkeypatch.setattr("spoc.core.deprecation.deprecated", mark)

    def original(a, b):
        return a + b

    alias = deprecated_alias(original, MESSAGE)

    with pytest.warns(DeprecationWarning, match="new_name"):
        assert alias(2, 3) == 5

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert original(2, 3) == 5


def test_alias_leaves_the_definition_unmarked(monkeypatch, mark):
    """A type checker reading ``__deprecated__`` must not flag the definition.

    Applying the decorator directly would: it marks the object it is given as
    well as the wrapper it returns.
    """
    monkeypatch.setattr("spoc.core.deprecation.deprecated", mark)

    def original():
        return "value"

    alias = deprecated_alias(original, MESSAGE)

    assert getattr(alias, "__deprecated__", None) == MESSAGE
    assert not hasattr(original, "__deprecated__")
    assert alias is not original


def test_alias_keeps_the_original_signature(monkeypatch, mark):
    """Documentation and ``help()`` must show the real thing, not ``*args``."""
    monkeypatch.setattr("spoc.core.deprecation.deprecated", mark)

    def documented(a, b, *, keyword=1):
        """A docstring that must not be lost."""
        return a + b + keyword

    alias = deprecated_alias(documented, MESSAGE)

    assert alias.__name__ == "documented"
    assert alias.__doc__ == "A docstring that must not be lost."
    assert str(inspect.signature(alias)) == "(a, b, *, keyword=1)"
