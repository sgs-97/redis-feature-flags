import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import tempfile
import os

from redis_flags.config import (
    read_config, write_config, get_env, get_redis_url
)


# ── read_config ────────────────────────────────────────────────


def test_read_config_returns_empty_when_file_missing():
    """
    Given: ~/.redis-flags.toml does not exist.
    Expected: read_config() returns empty dict — no error raised.
    """
    with patch("redis_flags.config.CONFIG_PATH") as mock_path:
        mock_path.exists.return_value = False
        result = read_config()
    assert result == {}


def test_read_config_returns_values_when_file_exists(tmp_path):
    """
    Given: ~/.redis-flags.toml contains redis_url and env.
    Expected: read_config() returns dict with both values.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('redis_url = "redis://localhost:6379"\nenv = "staging"\n')

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = read_config()

    assert result["redis_url"] == "redis://localhost:6379"
    assert result["env"] == "staging"


def test_read_config_returns_partial_values(tmp_path):
    """
    Given: ~/.redis-flags.toml contains only redis_url — no env.
    Expected: read_config() returns dict with just redis_url.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('redis_url = "redis://remote:6379"\n')

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = read_config()

    assert result["redis_url"] == "redis://remote:6379"
    assert "env" not in result


# ── write_config ───────────────────────────────────────────────


def test_write_config_creates_file(tmp_path):
    """
    Given: config file does not exist.
    After: write_config() called with data.
    Expected: file is created with correct content.
    """
    config_file = tmp_path / ".redis-flags.toml"

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        write_config({"env": "prod", "redis_url": "redis://localhost:6379"})

    assert config_file.exists()


def test_write_config_persists_values(tmp_path):
    """
    Given: write_config() called with env=prod.
    Expected: read_config() returns env=prod on next read.
    """
    config_file = tmp_path / ".redis-flags.toml"

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        write_config({"env": "prod"})
        result = read_config()

    assert result["env"] == "prod"


def test_write_config_overwrites_existing(tmp_path):
    """
    Given: config file already contains env=staging.
    After: write_config() called with env=prod.
    Expected: read_config() returns env=prod — old value overwritten.
    """
    config_file = tmp_path / ".redis-flags.toml"

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        write_config({"env": "staging"})
        write_config({"env": "prod"})
        result = read_config()

    assert result["env"] == "prod"


# ── get_env ────────────────────────────────────────────────────


def test_get_env_returns_override_when_provided():
    """
    Given: --env prod passed as override.
    Expected: get_env() returns prod regardless of config file.
    """
    result = get_env(env_override="prod")
    assert result == "prod"


def test_get_env_returns_config_value_when_no_override(tmp_path):
    """
    Given: no --env override. Config file contains env=staging.
    Expected: get_env() returns staging from config file.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('env = "staging"\n')

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = get_env(env_override=None)

    assert result == "staging"


def test_get_env_exits_when_neither_set(tmp_path):
    """
    Given: no --env override. Config file has no env field.
    Expected: get_env() raises SystemExit with code 1 — helpful error message.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('redis_url = "redis://localhost:6379"\n')

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        with pytest.raises(SystemExit) as exc:
            get_env(env_override=None)

    assert exc.value.code == 1


def test_get_env_exits_when_config_missing(tmp_path):
    """
    Given: no --env override. Config file does not exist.
    Expected: get_env() raises SystemExit with code 1.
    """
    config_file = tmp_path / ".redis-flags.toml"

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        with pytest.raises(SystemExit) as exc:
            get_env(env_override=None)

    assert exc.value.code == 1


def test_get_env_override_takes_priority_over_config(tmp_path):
    """
    Given: --env prod override AND config file contains env=staging.
    Expected: get_env() returns prod — override always wins.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('env = "staging"\n')

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = get_env(env_override="prod")

    assert result == "prod"


# ── get_redis_url ──────────────────────────────────────────────


def test_get_redis_url_returns_override_when_provided():
    """
    Given: --redis-url redis://remote:6379 passed as override.
    Expected: get_redis_url() returns the override URL.
    """
    result = get_redis_url(url_override="redis://remote:6379")
    assert result == "redis://remote:6379"


def test_get_redis_url_returns_config_value(tmp_path):
    """
    Given: no override. Config file contains redis_url=redis://remote:6379.
    Expected: get_redis_url() returns the config URL.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('redis_url = "redis://remote:6379"\n')

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = get_redis_url(url_override=None)

    assert result == "redis://remote:6379"


def test_get_redis_url_defaults_to_localhost(tmp_path):
    """
    Given: no override. Config file has no redis_url field.
    Expected: get_redis_url() returns redis://localhost:6379 — the default.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('env = "dev"\n')

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = get_redis_url(url_override=None)

    assert result == "redis://localhost:6379"


def test_get_redis_url_override_takes_priority_over_config(tmp_path):
    """
    Given: --redis-url override AND config file contains different redis_url.
    Expected: get_redis_url() returns the override — override always wins.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('redis_url = "redis://config-host:6379"\n')

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = get_redis_url(url_override="redis://override-host:6379")

    assert result == "redis://override-host:6379"