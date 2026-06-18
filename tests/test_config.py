"""Unit tests for configuration loading module."""

import pytest
from pathlib import Path

from ftp_doc_reader.config import load_config


@pytest.fixture
def tmp_env(tmp_path):
    """Helper fixture to create .env files for testing."""

    def _create_env(content: str) -> Path:
        env_file = tmp_path / ".env"
        env_file.write_text(content, encoding="utf-8")
        return env_file

    return _create_env


class TestLoadConfigSuccess:
    """Tests for successful configuration loading."""

    def test_load_valid_config_all_fields(self, tmp_env):
        """All fields specified should be loaded correctly."""
        env_file = tmp_env(
            "FTP_HOST=ftp.example.com\n"
            "FTP_PORT=2121\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
            "FTP_PROTOCOL=FTPS\n"
            "CACHE_DIR=/tmp/cache\n"
        )
        config = load_config(env_file)

        assert config.host == "ftp.example.com"
        assert config.port == 2121
        assert config.username == "user"
        assert config.password == "pass"
        assert config.protocol == "FTPS"
        assert config.cache_dir == Path("/tmp/cache")

    def test_load_config_defaults(self, tmp_env):
        """Optional fields should use default values when not specified."""
        env_file = tmp_env(
            "FTP_HOST=ftp.example.com\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
        )
        config = load_config(env_file)

        assert config.host == "ftp.example.com"
        assert config.port == 21
        assert config.username == "user"
        assert config.password == "pass"
        assert config.protocol == "FTP"
        assert config.cache_dir == Path(".cache")

    def test_protocol_case_insensitive(self, tmp_env):
        """Protocol value should be accepted case-insensitively."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
            "FTP_PROTOCOL=ftps\n"
        )
        config = load_config(env_file)
        assert config.protocol == "FTPS"

    def test_port_boundary_min(self, tmp_env):
        """Port value 1 should be accepted."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
            "FTP_PORT=1\n"
        )
        config = load_config(env_file)
        assert config.port == 1

    def test_port_boundary_max(self, tmp_env):
        """Port value 65535 should be accepted."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
            "FTP_PORT=65535\n"
        )
        config = load_config(env_file)
        assert config.port == 65535


class TestLoadConfigFailure:
    """Tests for configuration validation failures."""

    def test_missing_env_file(self, tmp_path):
        """Missing .env file should cause sys.exit(1)."""
        non_existent = tmp_path / ".env"
        with pytest.raises(SystemExit) as exc_info:
            load_config(non_existent)
        assert exc_info.value.code == 1

    def test_missing_host(self, tmp_env):
        """Missing FTP_HOST should cause sys.exit(1)."""
        env_file = tmp_env(
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(env_file)
        assert exc_info.value.code == 1

    def test_missing_username(self, tmp_env):
        """Missing FTP_USERNAME should cause sys.exit(1)."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_PASSWORD=pass\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(env_file)
        assert exc_info.value.code == 1

    def test_missing_password(self, tmp_env):
        """Missing FTP_PASSWORD should cause sys.exit(1)."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_USERNAME=user\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(env_file)
        assert exc_info.value.code == 1

    def test_missing_multiple_fields(self, tmp_env, capsys):
        """All missing required fields should be reported in one error message."""
        env_file = tmp_env("")
        with pytest.raises(SystemExit):
            load_config(env_file)
        captured = capsys.readouterr()
        assert "FTP_HOST" in captured.err
        assert "FTP_USERNAME" in captured.err
        assert "FTP_PASSWORD" in captured.err

    def test_empty_host(self, tmp_env):
        """Empty FTP_HOST should be treated as missing."""
        env_file = tmp_env(
            "FTP_HOST=  \n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(env_file)
        assert exc_info.value.code == 1

    def test_port_out_of_range_zero(self, tmp_env, capsys):
        """Port value 0 should be rejected."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
            "FTP_PORT=0\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(env_file)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "port" in captured.err.lower()

    def test_port_out_of_range_too_high(self, tmp_env, capsys):
        """Port value > 65535 should be rejected."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
            "FTP_PORT=65536\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(env_file)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "port" in captured.err.lower()

    def test_port_not_integer(self, tmp_env, capsys):
        """Non-integer port value should be rejected."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
            "FTP_PORT=abc\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(env_file)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "port" in captured.err.lower()

    def test_invalid_protocol(self, tmp_env, capsys):
        """Invalid protocol value should be rejected."""
        env_file = tmp_env(
            "FTP_HOST=host\n"
            "FTP_USERNAME=user\n"
            "FTP_PASSWORD=pass\n"
            "FTP_PROTOCOL=SFTP\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(env_file)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "protocol" in captured.err.lower()
