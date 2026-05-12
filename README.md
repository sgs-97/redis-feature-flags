# redis-feature-flags

[![PyPI version](https://badge.fury.io/py/redis-feature-flags.svg)](https://badge.fury.io/py/redis-feature-flags)
[![Python versions](https://img.shields.io/pypi/pyversions/redis-feature-flags)](https://pypi.org/project/redis-feature-flags)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/sgs-97/redis-feature-flags/actions/workflows/test-python.yml/badge.svg)](https://github.com/sgs-97/redis-feature-flags/actions)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/sgs-97/redis-feature-flags)

Feature flags for teams that already run Redis.
No new server. No monthly bill. No SaaS.

---

## Why redis-feature-flags?

- No new server — uses Redis you already run
- No monthly bill — completely free
- Data never leaves your infrastructure
- 60 second setup
- Works with any Redis instance — any host, any port
- Multiple environments on one Redis instance
- Python SDK + Java SDK + CLI included

📖 [Full documentation](docs/docs.md)

---

## Install
```bash
# Python SDK
pip install redis-feature-flags

# CLI
pip install redis-flags

# Java SDK
<dependency>
    <groupId>io.github.sgs-97</groupId>
    <artifactId>redis-feature-flags</artifactId>
    <version>1.0.0</version>
</dependency>
```

---

## 60-second quickstart
```python
import redis
from redis_feature_flags import FeatureFlags

r = redis.Redis()
flags = FeatureFlags(r, env="prod")

# Create a flag — disabled by default
flags.create("dark_mode", rollout=0)

# Enable it
flags.enable("dark_mode")

# Roll out to 10% of users
flags.set_rollout("dark_mode", 10)

# Evaluate
flags.is_enabled("dark_mode", user_id="alice")  # → True or False

# Kill switch — instant off for everyone, no redeploy
flags.disable("dark_mode")
```

---

## How it works

Every flag lives in Redis as a Hash:
```
ff:prod:flag:dark_mode  →  { enabled: "1", rollout: "10", ... }
```

`is_enabled()` evaluates in six steps — short-circuits at the first answer:
```
1. Flag exists?              No  → return default (False)
2. Flag enabled?             No  → return False
3. Flag expired?             Yes → return False
4. User in allowlist?        Yes → return True
5. User in allowed cohort?   Yes → return True
6. User in rollout bucket?   Yes → return True  /  No → return False
```

Rollout uses SHA-256 hashing of `flag_name:user_id` modulo 100.
Same user always gets the same answer — deterministic, no randomness.

---

## User targeting

Give specific users access regardless of rollout percentage:
```python
# Add alice to the flag — she always gets it
flags.add_user("dark_mode", "alice")

# Remove her
flags.remove_user("dark_mode", "alice")
```

---

## Cohort targeting

Group users into cohorts and target entire groups:
```python
# Create a cohort
flags.create_cohort("beta-testers")

# Add users
flags.add_to_cohort("beta-testers", "alice")
flags.add_to_cohort("beta-testers", "bob")

# Attach cohort to flag
flags.add_cohort_to_flag("dark_mode", "beta-testers")

# Now all beta-testers get dark_mode — regardless of rollout
flags.is_enabled("dark_mode", user_id="alice")  # → True
flags.is_enabled("dark_mode", user_id="charlie")  # → False (not in cohort)
```

---

## Flag expiry

Flags can auto-expire at a unix timestamp:
```python
import time

# Expire in 24 hours
flags.create("sale_banner", expires_at=int(time.time()) + 86400)
```

After the timestamp passes — `is_enabled()` returns `False` automatically.
No cleanup needed.

---

## Resilience — works when Redis is down

The SDK caches flag data locally (default TTL: 30 seconds):
```
Redis up   → serve from cache (fast) or fetch from Redis
Redis down → serve stale cache (last known state)
Redis down + nothing cached → return default value
```

Your application never crashes because Redis is temporarily unavailable.

---

## Multiple environments

Prod, staging, and dev share one Redis instance — no key collisions:
```python
prod    = FeatureFlags(r, env="prod")
staging = FeatureFlags(r, env="staging")
dev     = FeatureFlags(r, env="dev")

# Keys are namespaced — completely isolated
# ff:prod:flag:dark_mode
# ff:staging:flag:dark_mode
# ff:dev:flag:dark_mode
```

---

## CLI

Manage flags from your terminal:
```bash
# Set environment once
redis-flags use prod

# Create and manage flags
redis-flags create dark_mode --rollout 10
redis-flags enable dark_mode
redis-flags disable dark_mode
redis-flags set-rollout dark_mode 50

# See all flags
redis-flags list

┌───────────┬─────────┬─────────┬──────────────────┬──────────────────────┐
│ Flag      │ Enabled │ Rollout │ Updated by       │ Updated at           │
├───────────┼─────────┼─────────┼──────────────────┼──────────────────────┤
│ dark_mode │ yes     │ 50%     │ siripurapusravya │ 2026-03-27 19:55 UTC │
└───────────┴─────────┴─────────┴──────────────────┴──────────────────────┘

# Inspect a flag — full detail
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

# Cohort management
redis-flags create-cohort beta-testers
redis-flags add-to-cohort beta-testers alice
redis-flags inspect-cohort beta-testers
```

---

## Redis schema

All keys are namespaced. Your existing Redis data is never touched.
```
ff:{env}:flag:{name}              Hash   — flag data
ff:{env}:flag:{name}:users        Set    — user allowlist
ff:{env}:flag:{name}:cohorts      Set    — cohort allowlist
ff:{env}:cohort:{name}            Set    — cohort members
ff:{env}:user:{id}:cohorts        Set    — reverse index
ff:{env}:flags:__index__          Set    — all flag names
ff:{env}:cohorts:__index__        Set    — all cohort names
```

No `KEYS *` scans. Every operation is O(1) or O(log N).

---

## Supported languages

| Language | Package | Status |
|---|---|---|
| Python | [PyPI](https://pypi.org/project/redis-feature-flags) | stable |
| TypeScript | npm | coming soon |
| Go | go modules | coming soon |
| Java | [Maven Central](https://central.sonatype.com) | coming soon |

---

## Requirements

- Python 3.9+
- Redis 6.0+
- Java 17+

---

## License

MIT — [Gayatri Sravya Siripurapu](https://github.com/sgs-97)

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](.github/CONTRIBUTING.md).