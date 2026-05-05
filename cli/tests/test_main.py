import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from redis_flags.main import app

runner = CliRunner()


def test_use_command_sets_environment(tmp_path):
    """
    Given: redis-flags use staging called.
    Expected: exit code 0. Success message contains staging.
    """
    config_file = tmp_path / ".redis-flags.toml"
    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = runner.invoke(app, ["use", "staging"])
    assert result.exit_code == 0
    assert "staging" in result.output


def test_use_command_sets_prod(tmp_path):
    """
    Given: redis-flags use prod called.
    Expected: exit code 0. Success message contains prod.
    """
    config_file = tmp_path / ".redis-flags.toml"
    with patch("redis_flags.config.CONFIG_PATH", config_file):
        result = runner.invoke(app, ["use", "prod"])
    assert result.exit_code == 0
    assert "prod" in result.output


def test_status_shows_environment(tmp_path):
    """
    Given: config file contains env=staging.
    After: redis-flags status called.
    Expected: exit code 0. Output contains staging.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('env = "staging"\nredis_url = "redis://localhost:6379"\n')

    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        with patch("redis.Redis.from_url", return_value=mock_client):
            result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "staging" in result.output


def test_status_shows_redis_url(tmp_path):
    """
    Given: config file contains redis_url=redis://remote:6379.
    After: redis-flags status called.
    Expected: exit code 0. Output contains the Redis URL.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('env = "prod"\nredis_url = "redis://remote:6379"\n')

    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        with patch("redis.Redis.from_url", return_value=mock_client):
            result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "remote:6379" in result.output


def test_status_shows_connected_when_redis_up(tmp_path):
    """
    Given: Redis is reachable.
    After: redis-flags status called.
    Expected: output contains connected.
    """
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('env = "prod"\nredis_url = "redis://localhost:6379"\n')

    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        with patch("redis.Redis.from_url", return_value=mock_client):
            result = runner.invoke(app, ["status"])

    assert "connected" in result.output


def test_status_shows_unreachable_when_redis_down(tmp_path):
    """
    Given: Redis is unreachable.
    After: redis-flags status called.
    Expected: output contains unreachable.
    """
    import redis as redis_lib
    config_file = tmp_path / ".redis-flags.toml"
    config_file.write_text('env = "prod"\nredis_url = "redis://localhost:6379"\n')

    mock_client = MagicMock()
    mock_client.ping.side_effect = redis_lib.ConnectionError("down")

    with patch("redis_flags.config.CONFIG_PATH", config_file):
        with patch("redis.Redis.from_url", return_value=mock_client):
            result = runner.invoke(app, ["status"])

    assert "unreachable" in result.output