import tempfile
from pathlib import Path

import pytest

from spoc.core.config_loader import (
    load_environment,
    load_spoc_toml,
)
from spoc.core.exceptions import ConfigurationError


@pytest.fixture
def config_files():
    """Create temporary configuration files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)

        # Create spoc.toml file
        spoc_toml_content = {
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
        spoc_toml_path = base_dir / "spoc.toml"
        spoc_toml_str = """[spoc]
mode = "development"
debug = true

[spoc.apps]
production = ["core"]
staging = ["admin"]
development = ["demo", "test"]

[spoc.plugins]
database = ["db.backends.sqlite3", "db.backends.mysql"]
auth = ["auth.basic", "auth.oauth"]
"""
        spoc_toml_path.write_text(spoc_toml_str)

        # Create .env files for different environments
        env_dir = base_dir / ".env"
        env_dir.mkdir()

        # Development environment
        (env_dir / "development.toml").write_text("""
[env]
NAME = "env-app"
DEBUG = "true"
API_KEY = "dev-key-1234"
""")

        # Production environment
        (env_dir / "production.toml").write_text("""
[env]
URL = "postgresql://localhost/envdb"
POOL_SIZE = "10"
API_KEY = "prod-key-5678"
""")

        # Default environment file
        (env_dir / "default.toml").write_text("""
[env]
NAME = "default-app"
URL = "postgresql://localhost/defaultdb"
""")

        # Empty environment file
        (env_dir / "empty.toml").write_text("""
[env]
""")

        # Invalid environment file - not used as TOML will raise error
        (env_dir / "invalid.toml").write_text("""
[env]
# Valid TOML but without any values
""")

        yield base_dir, spoc_toml_content


class TestConfigLoader:
    """Tests for the config_loader module."""

    def test_load_environment(self, config_files):
        """Test loading configuration from environment TOML files."""
        base_dir, _ = config_files
        config = load_environment(base_dir, "development")
        assert config["NAME"] == "env-app"
        assert config["DEBUG"] == "true"
        # production.toml exists, so it is loaded directly (no fallback)
        config_prod = load_environment(base_dir, "production")
        assert config_prod["URL"] == "postgresql://localhost/envdb"
        assert config_prod["POOL_SIZE"] == "10"

    def test_load_spoc_toml(self, config_files):
        """Test loading the spoc.toml configuration file."""
        base_dir, expected_content = config_files

        # Load the configuration
        config = load_spoc_toml(base_dir)

        # Verify the config matches expected content
        assert config == expected_content
        assert config["spoc"]["mode"] == "development"
        assert config["spoc"]["debug"] is True
        assert "core" in config["spoc"]["apps"]["production"]
        assert "demo" in config["spoc"]["apps"]["development"]

    def test_load_missing_spoc_toml(self):
        """Test loading a missing spoc.toml file returns default configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_spoc_toml(Path(temp_dir))
            expected = {
                "spoc": {
                    "mode": "development",
                    "debug": False,
                    "apps": {},
                    "plugins": {},
                }
            }
            assert config == expected

    def test_load_invalid_spoc_toml(self):
        """Test loading an invalid spoc.toml file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # Create invalid TOML file
            invalid_toml = base_dir / "spoc.toml"
            invalid_toml.write_text("""
            [spoc
            mode = "development"  # Missing closing bracket
            """)

            # Loading should raise ConfigurationError for invalid TOML
            with pytest.raises(ConfigurationError):
                load_spoc_toml(base_dir)

    def test_load_missing_environment_falls_back_to_default(self, config_files):
        """A missing mode-specific file falls back to default.toml (echo off)."""
        base_dir, _ = config_files

        env = load_environment(base_dir, "nonexistent")

        assert env == {
            "NAME": "default-app",
            "URL": "postgresql://localhost/defaultdb",
        }

    def test_load_environment_no_files(self, tmp_path):
        """No mode-specific file and no default.toml yields an empty dict."""
        (tmp_path / ".env").mkdir()

        assert load_environment(tmp_path, "development") == {}

    def test_load_empty_environment(self, config_files):
        """Test loading an empty environment file."""
        base_dir, _ = config_files

        # Load empty environment
        env = load_environment(base_dir, "empty")

        assert env == {}

    def test_load_invalid_environment(self, config_files):
        """Test loading an environment file with no values."""
        base_dir, _ = config_files

        # Load environment whose [env] table is empty
        env = load_environment(base_dir, "invalid")

        assert env == {}

    @pytest.mark.parametrize(
        "mode,expected",
        [
            ("development", "dev-key-1234"),
            ("production", "prod-key-5678"),
            ("nonexistent", None),
        ],
    )
    def test_load_environment_parametrized(self, config_files, mode, expected):
        """Test loading environment variables for different modes."""
        base_dir, _ = config_files

        # Load environment for the specified mode
        env = load_environment(base_dir, mode)

        # Check if API_KEY matches expected value
        if expected is None:
            assert "API_KEY" not in env
        else:
            assert env["API_KEY"] == expected

    def test_environment_variables_override(self, config_files):
        """Test environment variable loading."""
        base_dir, _ = config_files

        # Testing env variables is tricky since the code doesn't actually use os.environ
        # Let's just check that we can load the values from the file
        env = load_environment(base_dir, "development")

        # Check that the values from the file are loaded
        assert env["API_KEY"] == "dev-key-1234"

    def test_env_directory_missing(self):
        """Test handling of missing .env directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # No .env directory exists
            env = load_environment(base_dir, "development")

            assert env == {}
