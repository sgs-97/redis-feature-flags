# redis-feature-flags

Feature flags for teams that already run Redis.
No new server. No new cost. Your data stays in your infrastructure.

📦 [PyPI](https://pypi.org/project/redis-feature-flags) · [Maven Central](https://central.sonatype.com/artifact/io.github.sgs-97/redis-feature-flags) · [CLI](https://pypi.org/project/redis-flags) · 📖 [Documentation](docs/docs.md)

---

## Why?

Most teams already run Redis. It sits in your stack as a cache or a session store. You are already paying for it, operating it, and trusting it.

Feature flag SaaS products charge hundreds of dollars a month for a server you do not need, send your user data to their infrastructure, and add another thing to monitor.

redis-feature-flags uses the Redis you already have. Nothing else.

---

## Who is this for?

- Startups and small teams who already run Redis and want to avoid adding new infrastructure
- Teams that are cost-conscious and want to eliminate SaaS subscriptions
- Developers who want full control over their data. No third party ever sees your flag evaluations
- Teams that value simplicity. No new service to deploy, monitor, or on-call for

If you already have Redis in your stack, this is a zero-overhead addition.

---

## What you get

**Gradual rollout** — release to 1%, then 10%, then 100%. Same user always gets the same answer. Deterministic, no randomness.

**User targeting** — give specific users early access regardless of rollout percentage.

**Cohort targeting** — target entire groups at once. Beta testers, enterprise users, internal teams.

**Kill switch** — disable any feature instantly for everyone. No redeploy. No waiting.

**Flag expiry** — auto-expire flags at a timestamp. No cleanup needed.

**Multiple environments** — prod, staging, and dev on one Redis instance. Fully isolated. No key collisions.

**Works when Redis is down** — stale cache keeps serving the last known state. Your application never crashes.

**CLI included** — manage flags from your terminal. Works with Python and Java SDKs.

**Well tested** — 94 Python SDK tests at 100% coverage, 109 Java tests, e2e tests against real Redis.

---

## Install

```bash
# Python SDK
pip install redis-feature-flags

# CLI
pip install redis-flags
```

```xml
<!-- Java SDK -->
<dependency>
    <groupId>io.github.sgs-97</groupId>
    <artifactId>redis-feature-flags</artifactId>
    <version>1.0.0</version>
</dependency>
```

---

## Quickstart

```python
import redis
from redis_feature_flags import FeatureFlags

r = redis.Redis()
flags = FeatureFlags(r, env="prod")

flags.create("dark_mode", rollout=10)
flags.enable("dark_mode")

flags.is_enabled("dark_mode", user_id="alice")  # → True or False

# Kill switch — instant off for everyone
flags.disable("dark_mode")
```

---

## CLI

```bash
redis-flags use prod
redis-flags create dark_mode --rollout 10
redis-flags enable dark_mode
redis-flags list
redis-flags inspect dark_mode
```

---

## Supported languages

| Language | Package | Status |
|---|---|---|
| Python | [PyPI](https://pypi.org/project/redis-feature-flags) | stable |
| Java | [Maven Central](https://central.sonatype.com/artifact/io.github.sgs-97/redis-feature-flags) | stable |
| TypeScript | npm | coming soon |
| Go | go modules | coming soon |

---

## Performance

- [Python SDK benchmarks](benchmarks/python/results.md)
- [Java SDK benchmarks](benchmarks/java/results.md)

---

## Requirements

- Python 3.9+ or Java 17+
- Redis 6.0+

---

## License

MIT — [Gayatri Sravya Siripurapu](https://github.com/sgs-97)

---

## Community

Contributions welcome.

- [Contributing Guide](.github/CONTRIBUTING.md) — how to set up, run tests, add a new SDK
- [Code of Conduct](.github/CODE_OF_CONDUCT.md) — community standards
- [Security Policy](.github/SECURITY.md) — how to report vulnerabilities privately
- [Report a bug](https://github.com/sgs-97/redis-feature-flags/issues/new?template=bug_report.md) — something is broken
- [Request a feature](https://github.com/sgs-97/redis-feature-flags/issues/new?template=feature_request.md) — suggest an idea

For security vulnerabilities do not open a public issue. See [SECURITY.md](.github/SECURITY.md).