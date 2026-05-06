# redis-feature-flags

Feature flags for teams that already run Redis.
No new server. No monthly bill. No SaaS.

---

## Table of Contents

- [Installation](#installation)
- [SDK](#sdk)
  - [Quickstart](#sdk-quickstart)
  - [Flags](#flags)
  - [Evaluation](#evaluation)
  - [User Targeting](#user-targeting)
  - [Cohorts](#cohorts)
  - [Expiry](#expiry)
  - [Environments](#environments)
  - [Cache](#cache)
  - [Exceptions](#exceptions)
- [CLI](#cli)
  - [Quickstart](#cli-quickstart)
  - [Context](#context)
  - [Flag Commands](#flag-commands)
  - [User Commands](#user-commands)
  - [Cohort Commands](#cohort-commands)
  - [History](#history)
- [Redis Schema](#redis-schema)
- [Changelog](#changelog)

---

## Installation

### Python SDK

```bash
pip install redis-feature-flags
```

### CLI

```bash
pip install redis-flags
```

### Requirements

- Python 3.9+
- Redis 6.0+

---

## SDK

### SDK Quickstart

```python
import redis
from redis_feature_flags import FeatureFlags

# Connect to your Redis — any host, any port
r = redis.Redis(host="localhost", port=6379)
flags = FeatureFlags(r, env="prod")

# Create a flag — disabled by default
flags.create("dark_mode", rollout=0)

# Enable it
flags.enable("dark_mode")

# Roll out to 10% of users
flags.set_rollout("dark_mode", 10)

# Evaluate for a user
flags.is_enabled("dark_mode", user_id="alice")  # → True or False

# Kill switch — instant off for everyone, no redeploy
flags.disable("dark_mode")
```

---

### Flags

#### `create(flag_name, rollout=0, created_by="unknown")`

Creates a new flag. Disabled by default.

```python
flags.create("dark_mode")
flags.create("dark_mode", rollout=10)
flags.create("dark_mode", rollout=10, created_by="alice")
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| flag_name | str | required | Unique flag name |
| rollout | int | 0 | Percentage 0-100 |
| created_by | str | unknown | Audit trail |

Raises `InvalidRolloutError` if rollout not between 0 and 100.

---

#### `enable(flag_name, updated_by="unknown")`

Enables a flag. Users in rollout, allowlist, or cohort will get it.

```python
flags.enable("dark_mode")
flags.enable("dark_mode", updated_by="alice")
```

Raises `FlagNotFoundError` if flag does not exist.

---

#### `disable(flag_name, updated_by="unknown")`

Disables a flag instantly for everyone. Kill switch.

```python
flags.disable("dark_mode")
```

Raises `FlagNotFoundError` if flag does not exist.

---

#### `set_rollout(flag_name, percent, updated_by="unknown")`

Updates rollout percentage.

```python
flags.set_rollout("dark_mode", 50)   # 50% of users
flags.set_rollout("dark_mode", 100)  # everyone
flags.set_rollout("dark_mode", 0)    # nobody
```

Raises `InvalidRolloutError` if percent not between 0 and 100.
Raises `FlagNotFoundError` if flag does not exist.

---

#### `delete(flag_name)`

Permanently deletes a flag and all associated data.

```python
flags.delete("dark_mode")
```

Deletes: flag Hash, user allowlist Set, cohort Set, history List.

---

#### `get(flag_name)`

Returns all flag fields as a dict.

```python
data = flags.get("dark_mode")
# {
#   "enabled": "0",
#   "rollout": "10",
#   "created_by": "alice",
#   "created_at": "1743101700",
#   "updated_by": "alice",
#   "updated_at": "1743101700",
#   "flag_version": "1",
#   "expires_at": "0"
# }
```

Raises `FlagNotFoundError` if flag does not exist.

---

#### `list_flags()`

Returns sorted list of all flag names.

```python
flags.list_flags()  # → ["dark_mode", "new_checkout"]
```

---

### Evaluation

#### `is_enabled(flag_name, user_id, default=False)`

Core evaluation method. Returns `True` or `False`.

```python
flags.is_enabled("dark_mode", user_id="alice")
flags.is_enabled("dark_mode", user_id="alice", default=True)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| flag_name | str | required | Flag to evaluate |
| user_id | str | required | User to evaluate for |
| default | bool | False | Return value if flag missing or Redis down |

#### Evaluation order — 6 steps

Evaluated in this exact order. Short-circuits at first answer.

| Step | Check | Result |
|---|---|---|
| 1 | Flag exists? | No → return default |
| 2 | Flag enabled? | No → return False |
| 3 | Flag expired? | Yes → return False |
| 4 | User in allowlist? | Yes → return True |
| 5 | User in cohort? | Yes → return True |
| 6 | User in rollout bucket? | Yes → True / No → False |

#### Deterministic rollout

Rollout uses SHA-256 hashing of `flag_name:user_id` modulo 100.
Same user always gets same answer. No randomness.

```
bucket = SHA-256("dark_mode:alice") % 100
if bucket < rollout → True
```

---

### User Targeting

Add specific users to a flag's allowlist. They always get the flag
regardless of rollout percentage.

#### `add_user(flag_name, user_id)`

```python
flags.add_user("dark_mode", "alice")
```

Raises `FlagNotFoundError` if flag does not exist.

#### `remove_user(flag_name, user_id)`

```python
flags.remove_user("dark_mode", "alice")
```

---

### Cohorts

Group users into named cohorts. Target entire groups at once.

#### `create_cohort(cohort_name)`

```python
flags.create_cohort("beta-testers")
```

#### `add_to_cohort(cohort_name, user_id)`

```python
flags.add_to_cohort("beta-testers", "alice")
flags.add_to_cohort("beta-testers", "bob")
```

#### `remove_from_cohort(cohort_name, user_id)`

```python
flags.remove_from_cohort("beta-testers", "alice")
```

#### `add_cohort_to_flag(flag_name, cohort_name)`

Attach a cohort to a flag. All cohort members get the flag.

```python
flags.add_cohort_to_flag("dark_mode", "beta-testers")
```

#### `remove_cohort_from_flag(flag_name, cohort_name)`

```python
flags.remove_cohort_from_flag("dark_mode", "beta-testers")
```

#### Full cohort example

```python
flags.create("dark_mode")
flags.enable("dark_mode")

flags.create_cohort("beta-testers")
flags.add_to_cohort("beta-testers", "alice")
flags.add_to_cohort("beta-testers", "bob")
flags.add_cohort_to_flag("dark_mode", "beta-testers")

flags.is_enabled("dark_mode", user_id="alice")    # → True
flags.is_enabled("dark_mode", user_id="charlie")  # → False
```

---

### Expiry

Flags auto-expire at a unix timestamp. No cleanup needed.

```python
import time

# Expire in 24 hours
flags.create("sale_banner", expires_at=int(time.time()) + 86400)

# Expire at specific datetime
from datetime import datetime, timezone
dt = datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)
flags.create("new_year_banner", expires_at=int(dt.timestamp()))
````

After timestamp passes — `is_enabled()` returns `False` automatically.
`expires_at=0` means never expires (default).

---

### Environments

Prod, staging, and dev share one Redis instance — no key collisions.

```python
prod    = FeatureFlags(r, env="prod")
staging = FeatureFlags(r, env="staging")
dev     = FeatureFlags(r, env="dev")
```

Keys are fully isolated:

````
ff:prod:flag:dark_mode
ff:staging:flag:dark_mode
ff:dev:flag:dark_mode
````

Creating a flag in prod never affects staging or dev.

---

### Cache

SDK caches flag data in-process. Default TTL: 30 seconds.

```python
# Custom TTL
flags = FeatureFlags(r, env="prod", cache_ttl=60)
```

#### Cache behavior

````
Redis up   → serve fresh cache (within TTL) or fetch from Redis
Redis down → serve stale cache (last known state, any age)
Redis down + nothing cached → return default value
````

#### Why stale cache matters

If Redis goes down — your application keeps working.
`is_enabled()` returns the last known flag state instead of crashing.

#### Cache invalidation

Cache is invalidated immediately on:
- `enable()`
- `disable()`
- `set_rollout()`
- `delete()`

Next `is_enabled()` call fetches fresh data from Redis.

---

### Exceptions

All exceptions inherit from `RedisFlagError`.
Catch base class to handle all library errors:

```python
from redis_feature_flags.exceptions import RedisFlagError

try:
    flags.enable("dark_mode")
except RedisFlagError as e:
    print(f"Flag error: {e}")
```

#### Exception reference

| Exception | When raised |
|---|---|
| `RedisFlagError` | Base class for all library errors |
| `FlagNotFoundError` | Flag does not exist — includes flag name and create hint |
| `CohortNotFoundError` | Cohort does not exist — includes cohort name and create hint |
| `InvalidRolloutError` | Rollout not between 0 and 100 |
| `RedisConnectionError` | Redis unreachable and no stale cache available |
| `SchemaVersionError` | Redis schema newer than SDK supports — upgrade SDK |

#### Examples

```python
from redis_feature_flags.exceptions import (
    FlagNotFoundError,
    InvalidRolloutError,
    RedisConnectionError,
)

# FlagNotFoundError
try:
    flags.enable("nonexistent")
except FlagNotFoundError as e:
    print(e)
    # Flag 'nonexistent' not found.
    # Create it with: flags.create('nonexistent')

# InvalidRolloutError
try:
    flags.create("dark_mode", rollout=150)
except InvalidRolloutError as e:
    print(e)
    # Rollout must be between 0 and 100. Got: 150

# RedisConnectionError
try:
    flags.is_enabled("dark_mode", user_id="alice")
except RedisConnectionError as e:
    print(e)
    # Redis unreachable and no cached data available
```

---

## CLI

### CLI Quickstart

```bash
# Install
pip install redis-flags

# Set environment
redis-flags use prod

# Create and manage flags
redis-flags create dark_mode --rollout 10
redis-flags enable dark_mode
redis-flags list
redis-flags inspect dark_mode
```

---

### Context

Every command needs an environment. Set it once — all commands use it.

#### `redis-flags use {env}`

Set persistent environment context.

```bash
redis-flags use prod
redis-flags use staging
redis-flags use dev
```

Saved to `~/.redis-flags.toml`:

```toml
env = "prod"
redis_url = "redis://localhost:6379"
```

#### `redis-flags status`

Show current environment and Redis connection.

```bash
redis-flags status

╭──────────────────────────────────────╮
│ Current context                      │
│ Environment   prod                   │
│ Redis URL     redis://localhost:6379 │
│ Redis         connected ✓            │
╰──────────────────────────────────────╯
```

#### Override for single command

```bash
redis-flags --env staging list
redis-flags --redis-url redis://remote:6379 list
```

#### Priority order

````
1. --env flag on command        highest priority
2. env in ~/.redis-flags.toml
3. neither set                  error with helpful message
````

---

### Flag Commands

#### `redis-flags create {flag}`

```bash
redis-flags create dark_mode
redis-flags create dark_mode --rollout 10
redis-flags create dark_mode --rollout 10 --created-by alice
```

| Option | Default | Description |
|---|---|---|
| --rollout | 0 | Percentage 0-100 |
| --created-by | OS username | Audit trail |

#### `redis-flags enable {flag}`

```bash
redis-flags enable dark_mode
redis-flags enable dark_mode --updated-by alice
```

#### `redis-flags disable {flag}`

```bash
redis-flags disable dark_mode
```

Instant kill switch — disables for everyone immediately.

#### `redis-flags set-rollout {flag} {percent}`

```bash
redis-flags set-rollout dark_mode 50
redis-flags set-rollout dark_mode 100
redis-flags set-rollout dark_mode 0
```

#### `redis-flags delete {flag}`

```bash
redis-flags delete dark_mode          # confirmation prompt
redis-flags delete dark_mode --yes    # skip confirmation
```

#### `redis-flags list`

```bash
redis-flags list

╭───────────┬─────────┬─────────┬──────────────────┬──────────────────────╮
│ Flag      │ Enabled │ Rollout │ Updated by       │ Updated at           │
├───────────┼─────────┼─────────┼──────────────────┼──────────────────────┤
│ dark_mode │ yes     │ 50%     │ siripurapusravya │ 2026-03-27 19:55 UTC │
╰───────────┴─────────┴─────────┴──────────────────┴──────────────────────╯
```

#### `redis-flags inspect {flag}`

```bash
redis-flags inspect dark_mode

╭────────── dark_mode ──────────╮
│ Enabled      yes              │
│ Rollout      50%              │
│ Version      1                │
│ Expires      never            │
│ Created by   alice            │
│ Created at   2026-03-27 UTC   │
│ Updated by   alice            │
│ Updated at   2026-03-27 UTC   │
│                               │
│ Users                         │
│   bob                         │
│                               │
│ Cohorts                       │
│   beta-testers                │
╰───────────────────────────────╯
```

---

### User Commands

#### `redis-flags add-user {flag} {user_id}`

Add user to flag allowlist. They always get the flag.

```bash
redis-flags add-user dark_mode alice
redis-flags add-user dark_mode bob
```

#### `redis-flags remove-user {flag} {user_id}`

```bash
redis-flags remove-user dark_mode alice
```

---

### Cohort Commands

#### `redis-flags create-cohort {name}`

```bash
redis-flags create-cohort beta-testers
```

#### `redis-flags delete-cohort {name}`

```bash
redis-flags delete-cohort beta-testers          # confirmation prompt
redis-flags delete-cohort beta-testers --yes    # skip confirmation
```

#### `redis-flags add-to-cohort {name} {user_id}`

```bash
redis-flags add-to-cohort beta-testers alice
redis-flags add-to-cohort beta-testers bob
```

#### `redis-flags remove-from-cohort {name} {user_id}`

```bash
redis-flags remove-from-cohort beta-testers alice
```

#### `redis-flags list-cohorts`

```bash
redis-flags list-cohorts

╭──────────────╮
│ Cohort       │
├──────────────┤
│ beta-testers │
╰──────────────╯
```

#### `redis-flags inspect-cohort {name}`

```bash
redis-flags inspect-cohort beta-testers

╭─ beta-testers ─╮
│ Members   2    │
│                │
│   alice        │
│   bob          │
╰────────────────╯
```

---

### History

Coming in v1.1:

```bash
redis-flags history dark_mode      # show version history
redis-flags rollback dark_mode --version 2  # restore previous version
```

---

## Redis Schema

All keys namespaced by environment. Existing Redis data never touched.

| Key | Type | Purpose |
|---|---|---|
| `ff:{env}:flag:{name}` | Hash | Flag object — all fields |
| `ff:{env}:flag:{name}:users` | Set | User allowlist |
| `ff:{env}:flag:{name}:cohorts` | Set | Cohort allowlist |
| `ff:{env}:flag:{name}:history` | List | Version history (v1.1) |
| `ff:{env}:cohort:{name}` | Set | Cohort members |
| `ff:{env}:user:{id}:cohorts` | Set | Reverse index |
| `ff:{env}:flags:__index__` | Set | All flag names |
| `ff:{env}:cohorts:__index__` | Set | All cohort names |
| `ff:{env}:__schema__` | String | Schema version |

No `KEYS *` scans. Every operation O(1) or O(log N).

### Flag Hash fields

| Field | Type | Description |
|---|---|---|
| enabled | "0" or "1" | Kill switch |
| rollout | "0"-"100" | Rollout percentage |
| expires_at | unix timestamp | "0" = never |
| created_at | unix timestamp | UTC |
| updated_at | unix timestamp | UTC |
| created_by | string | OS username |
| updated_by | string | OS username |
| flag_version | integer | Increments on change |

---

## Changelog

### v1.0.0 — 2026-03-27

- Python SDK — 94 tests, 100% coverage
- Python CLI — 68 tests, 95.83% coverage
- GitHub Actions CI — Python 3.9, 3.10, 3.11, 3.12, 3.13
- MIT License

### Roadmap

- v1.1 — history, rollback, schema version check, TLS support
- v2.0 — TypeScript SDK, Go SDK, Go CLI binary
- v3.0 — Java SDK, Spring Boot autoconfiguration
````

---

Save to `docs/docs.md`. Commit:

````bash
git add docs/docs.md
git commit -m "docs: complete documentation"
git push origin main
````