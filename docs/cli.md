# CLI

## Installation

```bash
pip install redis-flags
```

## Requirements

- Python 3.9+
- Redis 6.0+

---

## Quickstart

```bash
redis-flags use prod
redis-flags create dark_mode --rollout 10
redis-flags enable dark_mode
redis-flags list
redis-flags inspect dark_mode
```

---

## Connection

The CLI connects to Redis in this priority order:

```
1. --redis-url flag on command       highest priority
2. redis_url in ~/.redis-flags.toml
3. localhost:6379                    default
```

---

## Context

Every command needs an environment. Set it once — all commands use it.

### `redis-flags use {env}`

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

### `redis-flags status`

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

### Override for single command

```bash
redis-flags --env staging list
redis-flags --redis-url redis://remote:6379 list
```

---

## Flag Commands

### `redis-flags create {flag}`

```bash
redis-flags create dark_mode
redis-flags create dark_mode --rollout 10
redis-flags create dark_mode --rollout 10 --created-by alice
```

| Option | Default | Description |
|---|---|---|
| --rollout | 0 | Percentage 0-100 |
| --created-by | OS username | Audit trail |

### `redis-flags enable {flag}`

```bash
redis-flags enable dark_mode
redis-flags enable dark_mode --updated-by alice
```

### `redis-flags disable {flag}`

```bash
redis-flags disable dark_mode
```

Instant kill switch. Disables for everyone immediately.

### `redis-flags set-rollout {flag} {percent}`

```bash
redis-flags set-rollout dark_mode 50
redis-flags set-rollout dark_mode 100
redis-flags set-rollout dark_mode 0
```

### `redis-flags delete {flag}`

```bash
redis-flags delete dark_mode          # confirmation prompt
redis-flags delete dark_mode --yes    # skip confirmation
```

### `redis-flags list`

```bash
redis-flags list

╭───────────┬─────────┬─────────┬──────────────────┬──────────────────────╮
│ Flag      │ Enabled │ Rollout │ Updated by       │ Updated at           │
├───────────┼─────────┼─────────┼──────────────────┼──────────────────────┤
│ dark_mode │ yes     │ 50%     │ siripurapusravya │ 2026-03-27 19:55 UTC │
╰───────────┴─────────┴─────────┴──────────────────┴──────────────────────╯
```

### `redis-flags inspect {flag}`

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

## User Commands

### `redis-flags add-user {flag} {user_id}`

Add user to flag allowlist. They always get the flag.

```bash
redis-flags add-user dark_mode alice
redis-flags add-user dark_mode bob
```

### `redis-flags remove-user {flag} {user_id}`

```bash
redis-flags remove-user dark_mode alice
```

---

## Cohort Commands

### `redis-flags create-cohort {name}`

```bash
redis-flags create-cohort beta-testers
```

### `redis-flags delete-cohort {name}`

```bash
redis-flags delete-cohort beta-testers          # confirmation prompt
redis-flags delete-cohort beta-testers --yes    # skip confirmation
```

### `redis-flags add-to-cohort {name} {user_id}`

```bash
redis-flags add-to-cohort beta-testers alice
redis-flags add-to-cohort beta-testers bob
```

### `redis-flags remove-from-cohort {name} {user_id}`

```bash
redis-flags remove-from-cohort beta-testers alice
```

### `redis-flags list-cohorts`

```bash
redis-flags list-cohorts

╭──────────────╮
│ Cohort       │
├──────────────┤
│ beta-testers │
╰──────────────╯
```

### `redis-flags inspect-cohort {name}`

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

## History

Coming in v1.1:

```bash
redis-flags history dark_mode
redis-flags rollback dark_mode --version 2
```

---

## Audit trail

Every command that modifies a flag records who made the change. The CLI auto-detects your OS username:

```bash
redis-flags enable dark_mode
# updated_by = siripurapusravya (auto-detected)

redis-flags enable dark_mode --updated-by alice
# updated_by = alice (explicit)
```

All changes visible in `redis-flags inspect {flag}`.