"""
Tests for the canonical identifier grammar (spec: object-identity).

Validation rejects — it never normalizes.
"""

import pytest

from spoc.core.exceptions import InvalidSegmentError, MalformedIdentifierError
from spoc.core.identifier import Identifier, compose, parse, validate_segment


class TestSegmentValidation:
    @pytest.mark.parametrize(
        "value",
        ["post", "user_account", "a", "x9", "order_created", "int64", "a_b_c"],
    )
    def test_conforming_segments_accepted(self, value):
        assert validate_segment("object_name", value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "Post",  # uppercase
            "MyService",  # PascalCase
            "myService",  # camelCase
            "my-service",  # kebab
            "_private",  # leading underscore
            "9lives",  # leading digit
            "",  # empty
            "my.service",  # dot
            "my service",  # space
        ],
    )
    def test_nonconforming_segments_rejected(self, value):
        with pytest.raises(InvalidSegmentError) as exc:
            validate_segment("object_name", value)
        # The error names the segment and the offending value
        assert "object_name" in str(exc.value)
        assert repr(value) in str(exc.value)

    def test_no_normalization_ever(self):
        """A value that would conform after case-folding still fails."""
        with pytest.raises(InvalidSegmentError):
            validate_segment("kind", "Models")


class TestParse:
    def test_well_formed(self):
        parsed = parse("models:blog.post")
        assert parsed == Identifier(kind="models", namespace="blog", name="post")
        assert str(parsed) == "models:blog.post"

    @pytest.mark.parametrize(
        "identifier,fragment",
        [
            ("modelsblog.post", "missing ':'"),
            ("models:blogpost", "missing '.'"),
            ("models:blog.post.create", "operation suffix"),
            ("models:a.b.c.d", "operation suffix"),
        ],
    )
    def test_malformed_shapes_rejected(self, identifier, fragment):
        with pytest.raises(MalformedIdentifierError) as exc:
            parse(identifier)
        assert fragment in str(exc.value)

    def test_malformed_error_describes_grammar(self):
        with pytest.raises(MalformedIdentifierError) as exc:
            parse("nonsense")
        assert "kind:namespace.object_name" in str(exc.value)

    def test_invalid_segment_inside_shape(self):
        with pytest.raises(InvalidSegmentError):
            parse("models:Blog.post")

    def test_non_string_rejected(self):
        with pytest.raises(MalformedIdentifierError):
            parse(None)  # ty: ignore[invalid-argument-type]


class TestCompose:
    def test_round_trip(self):
        identifier = compose("models", "blog", "post")
        assert identifier == "models:blog.post"
        assert parse(identifier) == Identifier("models", "blog", "post")

    def test_compose_validates_every_segment(self):
        with pytest.raises(InvalidSegmentError):
            compose("models", "Blog", "post")
