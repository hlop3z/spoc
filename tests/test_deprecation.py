"""The deprecation signal required by the release policy.

Both paths are tested on every interpreter: the stdlib decorator when it exists,
and the 3.12 fallback always — a fallback exercised only on the one version CI
might not run is a fallback nobody has checked.
"""

from __future__ import annotations

import sys
import warnings

import pytest

from spoc.core.deprecation import _fallback_deprecated, deprecated

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
