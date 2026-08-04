"""
Tests for the configuration adapter (spec: project-configuration).

Ported from the config-loader tests, plus coverage of the explicit four-key validation
that replaced the generic recursive schema engine.
"""

import tempfile
from pathlib import Path

import pytest

from spoc.core.config import load_environment, load_spoc_toml, validate_spoc_config
from spoc.core.exceptions import ConfigurationError


@pytest.fixture
def config_files():
    """A project with spoc.toml and a set of environment files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)

        expected = {
            "spoc": {
                "mode": "development",
                "debug": True,
                "apps": {
                    "production": ["core"],
                    "staging": ["admin"],
                    "development": ["demo", "test"],
                },
                "plugins": {
                    "database": ["db.backends.sqlite3", "db.backends.mysql"],
                    "auth": ["auth.basic", "auth.oauth"],
                },
            }
        }
        (base_dir / "spoc.toml").write_text(
            '[spoc]\nmode = "development"\ndebug = true\n\n'
            "[spoc.apps]\n"
            'production = ["core"]\n'
            'staging = ["admin"]\n'
            'development = ["demo", "test"]\n\n'
            "[spoc.plugins]\n"
            'database = ["db.backends.sqlite3", "db.backends.mysql"]\n'
            'auth = ["auth.basic", "auth.oauth"]\n'
        )

        env_dir = base_dir / ".env"
        env_dir.mkdir()
        (env_dir / "development.toml").write_text(
            '[env]\nNAME = "env-app"\nDEBUG = "true"\nAPI_KEY = "dev-key-1234"\n'
        )
        (env_dir / "production.toml").write_text(
            "[env]\n"
            'URL = "postgresql://localhost/envdb"\n'
            'POOL_SIZE = "10"\n'
            'API_KEY = "prod-key-5678"\n'
        )
        (env_dir / "default.toml").write_text(
            '[env]\nNAME = "default-app"\nURL = "postgresql://localhost/defaultdb"\n'
        )
        (env_dir / "empty.toml").write_text("[env]\n")
        (env_dir / "invalid.toml").write_text("[env]\n# no values\n")

        yield base_dir, expected


class TestSpocToml:
    def test_load(self, config_files):
        base_dir, expected = config_files
        config = load_spoc_toml(base_dir)
        assert config == expected
        assert config["spoc"]["mode"] == "development"
        assert config["spoc"]["debug"] is True
        assert "core" in config["spoc"]["apps"]["production"]

    def test_missing_file_yields_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            assert load_spoc_toml(Path(temp_dir)) == {
                "spoc": {
                    "mode": "development",
                    "debug": False,
                    "apps": {},
                    "plugins": {},
                }
            }

    def test_absent_keys_fall_back_to_defaults(self, tmp_path):
        (tmp_path / "spoc.toml").write_text('[spoc]\nmode = "production"\n')
        config = load_spoc_toml(tmp_path)["spoc"]
        assert config["mode"] == "production"
        assert config["debug"] is False
        assert config["apps"] == {}

    def test_config_subdirectory_wins(self, tmp_path):
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "spoc.toml").write_text('[spoc]\nmode = "staging"\n')
        (tmp_path / "spoc.toml").write_text('[spoc]\nmode = "production"\n')
        assert load_spoc_toml(tmp_path)["spoc"]["mode"] == "staging"

    def test_malformed_toml_raises(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            (base_dir / "spoc.toml").write_text('[spoc\nmode = "development"\n')
            with pytest.raises(ConfigurationError):
                load_spoc_toml(base_dir)


class TestValidation:
    """The four explicit checks that replaced the recursive schema engine."""

    def test_absent_keys_are_not_errors(self):
        validate_spoc_config({"spoc": {}})
        validate_spoc_config({})

    @pytest.mark.parametrize(
        "key,bad_value,expected_type",
        [
            ("mode", 1, "str"),
            ("debug", "yes", "bool"),
            ("apps", ["core"], "dict"),
            ("plugins", "none", "dict"),
        ],
    )
    def test_wrong_type_named_with_its_path(self, key, bad_value, expected_type):
        with pytest.raises(ConfigurationError) as exc:
            validate_spoc_config({"spoc": {key: bad_value}})
        message = str(exc.value)
        assert f"spoc.{key}" in message
        assert expected_type in message

    def test_spoc_table_must_be_a_table(self):
        with pytest.raises(ConfigurationError, match="Expected dictionary for 'spoc'"):
            validate_spoc_config({"spoc": "not-a-table"})

    def test_every_error_is_reported_not_just_the_first(self):
        with pytest.raises(ConfigurationError) as exc:
            validate_spoc_config({"spoc": {"mode": 1, "debug": "yes"}})
        message = str(exc.value)
        assert "spoc.mode" in message and "spoc.debug" in message

    def test_unknown_keys_are_ignored(self):
        """The four keys are checked; anything else is the project's business."""
        validate_spoc_config({"spoc": {"mode": "development", "custom": object()}})


class TestEnvironment:
    def test_mode_specific_file(self, config_files):
        base_dir, _ = config_files
        assert load_environment(base_dir, "development")["NAME"] == "env-app"
        production = load_environment(base_dir, "production")
        assert production["URL"] == "postgresql://localhost/envdb"
        assert production["POOL_SIZE"] == "10"

    def test_missing_mode_falls_back_to_default(self, config_files):
        base_dir, _ = config_files
        assert load_environment(base_dir, "nonexistent") == {
            "NAME": "default-app",
            "URL": "postgresql://localhost/defaultdb",
        }

    def test_no_files_yields_empty(self, tmp_path):
        (tmp_path / ".env").mkdir()
        assert load_environment(tmp_path, "development") == {}

    def test_missing_env_directory_yields_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            assert load_environment(Path(temp_dir), "development") == {}

    @pytest.mark.parametrize("mode", ["empty", "invalid"])
    def test_empty_env_table_yields_empty(self, config_files, mode):
        base_dir, _ = config_files
        assert load_environment(base_dir, mode) == {}

    @pytest.mark.parametrize(
        "mode,expected",
        [
            ("development", "dev-key-1234"),
            ("production", "prod-key-5678"),
            ("nonexistent", None),
        ],
    )
    def test_api_key_per_mode(self, config_files, mode, expected):
        base_dir, _ = config_files
        env = load_environment(base_dir, mode)
        if expected is None:
            assert "API_KEY" not in env
        else:
            assert env["API_KEY"] == expected
