# Python SDK

## Installation

```bash
pip install redis-feature-flags
```

## Requirements

- Python 3.9+
- Redis 6.0+

---

## Quickstart

```python
import redis
from redis_feature_flags import FeatureFlags

r = redis.Redis(host="localhost", port=6379)
flags = FeatureFlags(r, env="prod")

flags.create("dark_mode", rollout=10)
flags.enable("dark_mode")

flags.is_enabled("dark_mode", user_id="alice")  # → True or False
```

---

## Configuration

```python
# Default TTL — 30 seconds
flags = FeatureFlags(r, env="prod")

# Custom TTL
flags = FeatureFlags(r, env="prod", cache_ttl=60)
```

---

## API Reference

### `is_enabled(flag_name, user_id, default=False)`

Evaluate a flag for a user. Returns `True` or `False`.

```python
flags.is_enabled("dark_mode", user_id="alice")
flags.is_enabled("dark_mode", user_id="alice", default=True)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| flag_name | str | required | Flag to evaluate |
| user_id | str | required | User to evaluate for |
| default | bool | False | Return value if flag missing or Redis down |

---

### `create(flag_name, rollout=0, created_by="unknown")`

Creates a new flag. Disabled by default.

```python
flags.create("dark_mode")
flags.create("dark_mode", rollout=10)
flags.create("dark_mode", rollout=10, created_by="alice")

# With expiry
import time
flags.create("sale_banner", expires_at=int(time.time()) + 86400)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| flag_name | str | required | Unique flag name |
| rollout | int | 0 | Percentage 0-100 |
| created_by | str | unknown | Audit trail |
| expires_at | int | 0 | Unix timestamp. 0 = never expires |

Raises `InvalidRolloutError` if rollout not between 0 and 100.

---

### `enable(flag_name, updated_by="unknown")`

Enables a flag.

```python
flags.enable("dark_mode")
flags.enable("dark_mode", updated_by="alice")
```

Raises `FlagNotFoundError` if flag does not exist.

---

### `disable(flag_name, updated_by="unknown")`

Disables a flag instantly for everyone. Kill switch.

```python
flags.disable("dark_mode")
flags.disable("dark_mode", updated_by="alice")
```

Raises `FlagNotFoundError` if flag does not exist.

---

### `set_rollout(flag_name, percent, updated_by="unknown")`

Updates rollout percentage.

```python
flags.set_rollout("dark_mode", 50)   # 50% of users
flags.set_rollout("dark_mode", 100)  # everyone
flags.set_rollout("dark_mode", 0)    # nobody
```

Raises `InvalidRolloutError` if percent not between 0 and 100.
Raises `FlagNotFoundError` if flag does not exist.

---

### `delete(flag_name)`

Permanently deletes a flag and all associated data.

```python
flags.delete("dark_mode")
```

---

### `get(flag_name)`

Returns all flag fields as a dict.

```python
data = flags.get("dark_mode")
# {
#   "enabled":      "1",
#   "rollout":      "10",
#   "created_by":   "alice",
#   "created_at":   "1743101700",
#   "updated_by":   "alice",
#   "updated_at":   "1743101700",
#   "flag_version": "1",
#   "expires_at":   "0"
# }
```

Raises `FlagNotFoundError` if flag does not exist.

---

### `list_flags()`

Returns sorted list of all flag names.

```python
flags.list_flags()  # → ["dark_mode", "new_checkout"]
```

---

## User Targeting

### `add_user(flag_name, user_id)`

Add user to flag allowlist. They always get the flag regardless of rollout.

```python
flags.add_user("dark_mode", "alice")
```

Raises `FlagNotFoundError` if flag does not exist.

### `remove_user(flag_name, user_id)`

```python
flags.remove_user("dark_mode", "alice")
```

---

## Cohort Targeting

### `create_cohort(cohort_name)`

```python
flags.create_cohort("beta-testers")
```

### `delete_cohort(cohort_name)`

```python
flags.delete_cohort("beta-testers")
```

### `add_to_cohort(cohort_name, user_id)`

```python
flags.add_to_cohort("beta-testers", "alice")
flags.add_to_cohort("beta-testers", "bob")
```

### `remove_from_cohort(cohort_name, user_id)`

```python
flags.remove_from_cohort("beta-testers", "alice")
```

### `add_cohort_to_flag(flag_name, cohort_name)`

Attach a cohort to a flag. All cohort members get the flag.

```python
flags.add_cohort_to_flag("dark_mode", "beta-testers")
```

### `remove_cohort_from_flag(flag_name, cohort_name)`

```python
flags.remove_cohort_from_flag("dark_mode", "beta-testers")
```

### Full cohort example

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

## Multiple environments

```python
prod    = FeatureFlags(r, env="prod")
staging = FeatureFlags(r, env="staging")
dev     = FeatureFlags(r, env="dev")
```

---

## Exceptions

All exceptions inherit from `RedisFlagError`.

```python
from redis_feature_flags.exceptions import RedisFlagError

try:
    flags.enable("dark_mode")
except RedisFlagError as e:
    print(e)
```

| Exception | When raised |
|---|---|
| `RedisFlagError` | Base class for all library errors |
| `FlagNotFoundError` | Flag does not exist |
| `CohortNotFoundError` | Cohort does not exist |
| `InvalidRolloutError` | Rollout not between 0 and 100 |
| `RedisConnectionError` | Redis unreachable and no stale cache available |
| `SchemaVersionError` | Redis schema newer than SDK supports |

### Examples

```python
from redis_feature_flags.exceptions import (
    FlagNotFoundError,
    InvalidRolloutError,
    RedisConnectionError,
)

try:
    flags.enable("nonexistent")
except FlagNotFoundError as e:
    print(e)
    # Flag 'nonexistent' not found.
    # Create it with: flags.create('nonexistent')

try:
    flags.create("dark_mode", rollout=150)
except InvalidRolloutError as e:
    print(e)
    # Rollout must be between 0 and 100. Got: 150
```