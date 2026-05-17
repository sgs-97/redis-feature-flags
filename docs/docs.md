# redis-feature-flags

Feature flags backed by Redis. No new server. No new cost. Your data stays in your infrastructure.

---

## Documentation

- [Python SDK](python.md)
- [Java SDK](java.md)
- [CLI](cli.md)
- [Changelog](../CHANGELOG.md)

---

## Available operations

### Flag management

| Operation | Description |
|---|---|
| `create(flag_name)` | Create a new flag. Disabled by default. |
| `enable(flag_name)` | Enable a flag for evaluation. |
| `disable(flag_name)` | Disable a flag instantly. Kill switch. |
| `set_rollout(flag_name, percent)` | Set rollout percentage 0-100. |
| `delete(flag_name)` | Permanently delete a flag and all its data. |
| `get(flag_name)` | Get all flag fields. |
| `list_flags()` | List all flag names. |

### Evaluation

| Operation | Description |
|---|---|
| `is_enabled(flag_name, user_id)` | Evaluate a flag for a user. Returns True or False. |

### User targeting

| Operation | Description |
|---|---|
| `add_user(flag_name, user_id)` | Add user to flag allowlist. Always gets the flag. |
| `remove_user(flag_name, user_id)` | Remove user from allowlist. |

### Cohort targeting

| Operation | Description |
|---|---|
| `create_cohort(cohort_name)` | Create a named cohort. |
| `delete_cohort(cohort_name)` | Delete a cohort. |
| `add_to_cohort(cohort_name, user_id)` | Add user to cohort. |
| `remove_from_cohort(cohort_name, user_id)` | Remove user from cohort. |
| `add_cohort_to_flag(flag_name, cohort_name)` | Attach cohort to flag. |
| `remove_cohort_from_flag(flag_name, cohort_name)` | Detach cohort from flag. |
| `list_cohorts()` | List all cohort names. |

---

## Evaluation algorithm

Every `is_enabled()` call evaluates in six steps. Short-circuits at the first answer.

| Step | Check | Result |
|---|---|---|
| 1 | Flag exists? | No → return default |
| 2 | Flag enabled? | No → return False |
| 3 | Flag expired? | Yes → return False |
| 4 | User in allowlist? | Yes → return True |
| 5 | User in cohort? | Yes → return True |
| 6 | User in rollout bucket? | Yes → True / No → False |

Rollout uses SHA-256 hashing of `flag_name:user_id` modulo 100. Same user always gets same answer. No randomness.

---

## Cache

SDK caches flag data in-process. Default TTL: 30 seconds.

```
Redis up   → serve fresh cache or fetch from Redis
Redis down → serve stale cache (last known state)
Redis down + nothing cached → return default value
```

Cache is invalidated immediately on `enable()`, `disable()`, `set_rollout()`, `delete()`.

See language-specific docs for cache configuration.

---

## Redis schema

All keys namespaced by environment. Your existing Redis data is never touched.

| Key | Type | Purpose |
|---|---|---|
| `ff:{env}:flag:{name}` | Hash | Flag object |
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

## Supported languages

| Language | Package | Status |
|---|---|---|
| Python | [PyPI](https://pypi.org/project/redis-feature-flags) | stable |
| Java | [Maven Central](https://central.sonatype.com/artifact/io.github.sgs-97/redis-feature-flags) | stable |
| TypeScript | npm | coming soon |
| Go | go modules | coming soon |


## CLI

| Package | Status |
|---|---|
| [PyPI](https://pypi.org/project/redis-flags) | stable |

---

## Roadmap

- v1.1 — history, rollback, schema version check, TLS support
- v2.0 — TypeScript SDK, Go SDK, Go CLI binary