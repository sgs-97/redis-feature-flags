import pytest
from unittest.mock import patch, MagicMock
import redis as redis_lib

from redis_flags.connection import get_client


def test_get_client_returns_client_when_connected():
    """
    Given: Redis is reachable — ping returns True.
    Expected: get_client() returns a Redis client instance.
    """
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch("redis.Redis.from_url", return_value=mock_client):
        client = get_client("redis://localhost:6379")

    assert client is mock_client


def test_get_client_exits_on_connection_error():
    """
    Given: Redis is unreachable — ConnectionError raised on ping.
    Expected: get_client() raises SystemExit with code 1.
    """
    mock_client = MagicMock()
    mock_client.ping.side_effect = redis_lib.ConnectionError("refused")

    with patch("redis.Redis.from_url", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            get_client("redis://localhost:6379")

    assert exc.value.code == 1


def test_get_client_exits_on_auth_error():
    """
    Given: Redis requires authentication — AuthenticationError raised on ping.
    Expected: get_client() raises SystemExit with code 1.
    """
    mock_client = MagicMock()
    mock_client.ping.side_effect = redis_lib.AuthenticationError("auth failed")

    with patch("redis.Redis.from_url", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            get_client("redis://localhost:6379")

    assert exc.value.code == 1


def test_get_client_calls_from_url_with_correct_url():
    """
    Given: custom Redis URL redis://remote:6379.
    Expected: from_url() is called with that exact URL.
    """
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch("redis.Redis.from_url", return_value=mock_client) as mock_from_url:
        get_client("redis://remote:6379")

    mock_from_url.assert_called_once_with(
        "redis://remote:6379",
        decode_responses=False
    )

def test_get_client_exits_with_helpful_message_on_auth_error(capsys):
    """
    Given: Redis raises AuthenticationError on ping.
    Expected: SystemExit raised — helpful message shown.
    """
    from unittest.mock import MagicMock
    import redis as redis_lib
    mock_client = MagicMock()
    mock_client.ping.side_effect = redis_lib.AuthenticationError("auth failed")
    with patch("redis.Redis.from_url", return_value=mock_client):
        with pytest.raises(SystemExit):
            get_client("redis://:wrongpass@localhost:6379")