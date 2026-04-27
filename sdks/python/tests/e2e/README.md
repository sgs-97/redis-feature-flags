# End-to-End Tests

## What are e2e tests?

Unit tests use fakeredis — a simulated Redis that runs in memory.
E2e tests use real Redis — the same Redis a developer runs in production.

This matters because:

- fakeredis simulates Redis behavior but is not Redis
- Real Redis has different byte encoding, connection pooling, and edge cases
- A bug that passes unit tests may fail against real Redis
- E2e tests simulate exactly what a developer experiences after pip install

## What e2e tests cover

test_flag_lifecycle.py   Full create → enable → disable → delete workflow
test_evaluation.py       is_enabled() correctness against real Redis
test_cohorts.py          Cohort targeting end to end
test_cache.py            Cache behavior and Redis-down resilience
test_environments.py     Prod, staging, dev isolation
test_cli.py              CLI commands against real Redis
Cross-verification — SDK creates, CLI reads and vice versa

## How to run

Start a dedicated Redis instance on port 6399:

```bash
redis-server --port 6399 --daemonize yes
```

Run e2e tests:

```bash
cd sdks/python
pytest tests/e2e/ -v
```

Stop Redis when done:

```bash
redis-cli -p 6399 shutdown
```

## Why port 6399?

E2e tests use port 6399 — not 6379 — to avoid touching your local
Redis data. Every test run starts with a clean slate on port 6399.

## Isolation

Every test cleans up after itself. A conftest.py fixture flushes
the test database before each test — no data leaks between tests.

## Cross-verification tests

The most important e2e tests verify SDK and CLI are compatible:

SDK creates flag  → CLI list shows it
CLI creates flag  → SDK is_enabled() evaluates it
CLI enables flag  → SDK is_enabled() returns True
CLI disables flag → SDK is_enabled() returns False

These tests catch schema mismatches between SDK and CLI that
unit tests cannot catch because both use the same fakeredis instance.

## CI/CD

E2e tests run automatically on every push via GitHub Actions.
A real Redis service is started in the CI environment.
See .github/workflows/test-python.yml for configuration.