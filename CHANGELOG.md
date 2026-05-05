# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-27

### Added

**Python SDK** (`sdks/python`)
- `FeatureFlags` client — core public API
- `is_enabled(flag_name, user_id, default)` — 6-step evaluation algorithm
- Deterministic rollout via SHA-256 hashing — same user always same answer
- In-process cache with 30 second TTL — sub-millisecond evaluation
- Stale cache fallback — works when Redis is down
- User allowlist targeting — `add_user()`, `remove_user()`
- Cohort targeting — bidirectional index via Redis pipeline
- Flag expiry — auto-expires at unix timestamp
- Multiple environments — prod, staging, dev on one Redis instance
- Full exception hierarchy with actionable error messages
- 94 tests — 100% coverage
- Python 3.9+ support

**Python CLI** (`cli/`)
- `redis-flags use {env}` — persistent environment context
- `redis-flags status` — current context and Redis connection
- `redis-flags create/enable/disable/set-rollout/delete` — flag management
- `redis-flags list/inspect` — rich table and panel output
- `redis-flags add-user/remove-user` — user targeting
- `redis-flags create-cohort/delete-cohort` — cohort management
- `redis-flags add-to-cohort/remove-from-cohort` — cohort membership
- `redis-flags list-cohorts/inspect-cohort` — cohort output
- Auto-detects OS username for audit trail via `getpass.getuser()`
- UTC timestamps everywhere
- Confirmation prompts on destructive commands
- 68 tests — 95.83% coverage

**Infrastructure**
- Monorepo structure — sdks/, cli/, spec/, docs/
- Shared evaluation spec — `spec/evaluation_spec.json`
- GitHub Actions CI — Python 3.9, 3.10, 3.11, 3.12, 3.13
- MIT License