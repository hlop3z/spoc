"""
Tests for canonical identity (spec: object-identity).

Validation rejects — it never normalizes. Conversion is a separate step that applies only
to names the kernel *derives*, never to names the author *states*.
"""

import pytest

from spoc.core.exceptions import InvalidSegmentError, MalformedIdentifierError
from spoc.core.identity import (
    Identifier,
    compose,
    parse,
    to_snake_case,
    validate_segment,
)


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
        assert "object_name" in str(exc.value)
        assert repr(value) in str(exc.value)

    def test_no_normalization_ever(self):
        """A value that would conform after case-folding still fails."""
        with pytest.raises(InvalidSegmentError):
            validate_segment("kind", "Models")


class TestSnakeCaseDerivation:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("Post", "post"),
            ("MyService", "my_service"),
            ("UserAccount", "user_account"),
            ("CommentThread", "comment_thread"),
            ("HTTPServer", "http_server"),
            ("Post2", "post2"),
            ("already_snake", "already_snake"),
            ("kebab-case-name", "kebab_case_name"),
            ("camelCaseName", "camel_case_name"),
            ("__dunder__", "dunder"),
        ],
    )
    def test_conversion(self, value, expected):
        assert to_snake_case(value) == expected

    def test_acronym_boundary_is_not_collapsed(self):
        """Without the acronym rule, HTTPServer would become 'httpserver'."""
        assert to_snake_case("HTTPServer") == "http_server"
        assert to_snake_case("parseHTTPResponse") == "parse_http_response"

    def test_conversion_feeds_validation_not_replaces_it(self):
        """Conversion is not a guess — a leading digit still fails validation."""
        assert to_snake_case("2Cool") == "2_cool"
        with pytest.raises(InvalidSegmentError):
            validate_segment("object_name", to_snake_case("2Cool"))


class TestParse:
    def test_well_formed(self):
        parsed = parse("models:blog.post")
        assert parsed == Identifier(kind="models", namespace="blog", object_name="post")
        assert str(parsed) == "models:blog.post"

    def test_segments_carry_the_grammars_own_names(self):
        """One vocabulary: the grammar, the record, and the errors all agree."""
        assert parse("models:blog.post")._fields == ("kind", "namespace", "object_name")

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
