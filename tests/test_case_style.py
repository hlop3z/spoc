"""
Tests for case conversion.

``to_snake_case`` is load-bearing: it derives the object_name segment of
every identifier whose name is not stated explicitly (spec: object-identity,
"derived name converted from conventional class casing").
"""

import pytest

from spoc.case_style import (
    case_style,
    is_valid_case_style,
    to_camel_case,
    to_kebab_case,
    to_pascal_case,
    to_snake_case,
)


class TestToSnakeCase:
    @pytest.mark.parametrize(
        "value,expected",
        [
            # Already conforming — unchanged
            ("post", "post"),
            ("user_account", "user_account"),
            ("list_posts", "list_posts"),
            # PEP 8 class names — the identifier derivation path
            ("Post", "post"),
            ("UserAccount", "user_account"),
            ("CommentThread", "comment_thread"),
            # camelCase
            ("userAccount", "user_account"),
            ("parseURLFast", "parse_url_fast"),
            # Acronyms keep their word boundary
            ("HTTPServer", "http_server"),
            ("HTTPSConnection", "https_connection"),
            ("XMLHttpRequest", "xml_http_request"),
            ("APIKey", "api_key"),
            ("IOError", "io_error"),
            ("PostID", "post_id"),
            # Bare acronyms have no internal boundary
            ("HTTP", "http"),
            ("ID", "id"),
            ("A", "a"),
            # Digits
            ("Post2", "post2"),
            ("Base64Encoder", "base64_encoder"),
            # Separators normalize and collapse
            ("Test-String", "test_string"),
            ("Test--String", "test_string"),
            ("__Test__String__", "test_string"),
            ("", ""),
        ],
    )
    def test_conversion(self, value, expected):
        assert to_snake_case(value) == expected

    def test_is_idempotent(self):
        """Converting an already-converted name changes nothing."""
        for value in ("HTTPServer", "UserAccount", "parseURLFast"):
            once = to_snake_case(value)
            assert to_snake_case(once) == once

    def test_clip_edges_false_pads(self):
        assert to_snake_case("Post", clip_edges=False) == "_post_"


class TestOtherStyles:
    @pytest.mark.parametrize(
        "value,expected",
        [("user_account", "UserAccount"), ("HTTPServer", "HttpServer")],
    )
    def test_pascal(self, value, expected):
        assert to_pascal_case(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [("user_account", "userAccount"), ("", "")],
    )
    def test_camel(self, value, expected):
        assert to_camel_case(value) == expected

    def test_kebab(self):
        assert to_kebab_case("UserAccount") == "user-account"


class TestCaseStyle:
    @pytest.mark.parametrize(
        "mode,expected",
        [
            ("snake", "user_account"),
            ("camel", "userAccount"),
            ("pascal", "UserAccount"),
            ("kebab", "user-account"),
        ],
    )
    def test_dispatch(self, mode, expected):
        assert case_style("UserAccount", mode) == expected

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError, match="Invalid case style"):
            case_style("x", "shouty")  # type: ignore[arg-type]

    def test_is_valid_case_style(self):
        assert is_valid_case_style("snake")
        assert not is_valid_case_style("shouty")
