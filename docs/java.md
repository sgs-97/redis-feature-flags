# Java SDK

## Installation

### Maven

```xml
<dependency>
    <groupId>io.github.sgs-97</groupId>
    <artifactId>redis-feature-flags</artifactId>
    <version>1.0.0</version>
</dependency>
```

### Requirements

- Java 17+
- Redis 6.0+

---

## Spring Boot

Add dependency and configure in `application.yml`:

```yaml
redis-feature-flags:
  env: prod
  redis-url: redis://localhost:6379
  cache-ttl: 30
```

Autowire and use:

```java
@Autowired
FeatureFlags flags;

flags.isEnabled("dark_mode", "alice");
```

---

## Standalone usage

```java
import com.redisfeatureflags.FeatureFlags;
import redis.clients.jedis.JedisPool;

JedisPool pool = new JedisPool("localhost", 6379);
FeatureFlags flags = new FeatureFlags(pool, "prod");
```

Custom cache TTL:

```java
FeatureFlags flags = new FeatureFlags(pool, "prod", 60);
```

---

## API Reference

### `isEnabled(flagName, userId)`

Evaluate a flag for a user. Returns `true` or `false`.

```java
flags.isEnabled("dark_mode", "alice");
flags.isEnabled("dark_mode", "alice", true); // custom default
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| flagName | String | required | Flag to evaluate |
| userId | String | required | User to evaluate for |
| defaultValue | boolean | false | Return value if flag missing or Redis down |

---

### `create(flagName, rollout, createdBy)`

Creates a new flag. Disabled by default.

```java
flags.create("dark_mode");
flags.create("dark_mode", 10);
flags.create("dark_mode", 10, "alice");
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| flagName | String | required | Unique flag name |
| rollout | int | 0 | Percentage 0-100 |
| createdBy | String | unknown | Audit trail |

Throws `InvalidRolloutError` if rollout not between 0 and 100.

---

### `enable(flagName)`

Enables a flag.

```java
flags.enable("dark_mode");
flags.enable("dark_mode", "alice"); // with audit trail
```

Throws `FlagNotFoundError` if flag does not exist.

---

### `disable(flagName)`

Disables a flag instantly for everyone. Kill switch.

```java
flags.disable("dark_mode");
flags.disable("dark_mode", "alice"); // with audit trail
```

Throws `FlagNotFoundError` if flag does not exist.

---

### `setRollout(flagName, percent)`

Updates rollout percentage.

```java
flags.setRollout("dark_mode", 50);   // 50% of users
flags.setRollout("dark_mode", 100);  // everyone
flags.setRollout("dark_mode", 0);    // nobody
```

Throws `InvalidRolloutError` if percent not between 0 and 100.
Throws `FlagNotFoundError` if flag does not exist.

---

### `delete(flagName)`

Permanently deletes a flag and all associated data.

```java
flags.delete("dark_mode");
```

---

### `get(flagName)`

Returns all flag fields as a Map.

```java
Map<String, String> data = flags.get("dark_mode");
// {
//   "enabled":      "1",
//   "rollout":      "10",
//   "created_by":   "alice",
//   "created_at":   "1743101700",
//   "flag_version": "1",
//   "expires_at":   "0"
// }
```

Throws `FlagNotFoundError` if flag does not exist.

---

### `listFlags()`

Returns sorted list of all flag names.

```java
List<String> flags = flags.listFlags();
// ["dark_mode", "new_checkout"]
```

---

## User Targeting

### `addUser(flagName, userId)`

Add user to flag allowlist. They always get the flag regardless of rollout.

```java
flags.addUser("dark_mode", "alice");
```

### `removeUser(flagName, userId)`

```java
flags.removeUser("dark_mode", "alice");
```

---

## Cohort Targeting

### `createCohort(cohortName)`

```java
flags.createCohort("beta-testers");
```

### `addToCohort(cohortName, userId)`

```java
flags.addToCohort("beta-testers", "alice");
flags.addToCohort("beta-testers", "bob");
```

### `removeFromCohort(cohortName, userId)`

```java
flags.removeFromCohort("beta-testers", "alice");
```

### `addCohortToFlag(flagName, cohortName)`

Attach a cohort to a flag. All cohort members get the flag.

```java
flags.addCohortToFlag("dark_mode", "beta-testers");
```

### `removeCohortFromFlag(flagName, cohortName)`

```java
flags.removeCohortFromFlag("dark_mode", "beta-testers");
```

### Full cohort example

```java
flags.create("dark_mode");
flags.enable("dark_mode");

flags.createCohort("beta-testers");
flags.addToCohort("beta-testers", "alice");
flags.addToCohort("beta-testers", "bob");
flags.addCohortToFlag("dark_mode", "beta-testers");

flags.isEnabled("dark_mode", "alice");    // → true
flags.isEnabled("dark_mode", "charlie");  // → false
```

---

## Exceptions

All exceptions extend `RedisFlagError`.

```java
import com.redisfeatureflags.exceptions.RedisFlagError;

try {
    flags.enable("dark_mode");
} catch (RedisFlagError e) {
    System.out.println(e.getMessage());
}
```

| Exception | When raised |
|---|---|
| `RedisFlagError` | Base class for all library errors |
| `FlagNotFoundError` | Flag does not exist |
| `CohortNotFoundError` | Cohort does not exist |
| `InvalidRolloutError` | Rollout not between 0 and 100 |
| `RedisConnectionError` | Redis unreachable and no stale cache available |
| `SchemaVersionError` | Redis schema newer than SDK supports |

---

## Cache

SDK caches flag data in-process. Default TTL: 30 seconds.

```java
// Custom TTL — 60 seconds
FeatureFlags flags = new FeatureFlags(pool, "prod", 60);
```

```
Redis up   → serve fresh cache or fetch from Redis
Redis down → serve stale cache (last known state)
Redis down + nothing cached → return default value
```

Cache is invalidated immediately on `enable()`, `disable()`, `setRollout()`, `delete()`.

---

## Multiple environments

```java
FeatureFlags prod    = new FeatureFlags(pool, "prod");
FeatureFlags staging = new FeatureFlags(pool, "staging");
FeatureFlags dev     = new FeatureFlags(pool, "dev");
```

Keys are fully isolated:

```
ff:prod:flag:dark_mode
ff:staging:flag:dark_mode
ff:dev:flag:dark_mode
```