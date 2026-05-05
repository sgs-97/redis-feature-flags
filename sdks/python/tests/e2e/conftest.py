# sdks/python/tests/e2e/conftest.py

"""
E2e test configuration.

Uses a real Redis instance on port 6399.
Start before running:
    redis-server --port 6399 --daemonize yes

Every test gets a clean Redis state via the redis_client fixture.
The fixture flushes all keys with prefix ff:e2etest: after each test.
"""

from __future__ import annotations

import subprocess
import pytest
import redis

# ── Constants ──────────────────────────────────────────────────

from .constants import E2E_REDIS_PORT, E2E_ENV


# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture(scope="session")
def redis_client():
    """
    Session-scoped real Redis client.
    Connects once — shared across all e2e tests.
    Fails clearly if Redis is not running on port 6399.
    """
    try:
        client = redis.Redis(host="localhost", port=E2E_REDIS_PORT)
        client.ping()
        return client
    except redis.ConnectionError:
        pytest.fail(
            f"\n\nCannot connect to Redis on port {E2E_REDIS_PORT}.\n"
            f"Start it with:\n"
            f"    redis-server --port {E2E_REDIS_PORT} --daemonize yes\n"
        )


@pytest.fixture(autouse=True)
def clean_redis(redis_client):
    """
    Auto-used fixture — runs before and after every e2e test.
    Deletes all keys with prefix ff:e2etest: before each test.
    Guarantees every test starts with a clean slate.
    Does not touch keys outside ff:e2etest: namespace.
    """
    _flush_test_keys(redis_client)
    yield
    _flush_test_keys(redis_client)


def _flush_test_keys(client: redis.Redis) -> None:
    """Delete all keys in the e2etest environment namespace."""
    pattern = f"ff:{E2E_ENV}:*"
    keys = client.keys(pattern)
    if keys:
        client.delete(*keys)
        