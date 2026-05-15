# Contributing to redis-feature-flags

Thank you for your interest in contributing. This document explains how to get started.

---

## What we need help with

- TypeScript SDK
- Go SDK + CLI binary
- Bug fixes
- Documentation improvements
- Test coverage improvements

---

## Development setup

### Prerequisites

- Python 3.9+
- Java 17+
- Redis 6.0+
- Maven 3.8+

### Clone the repo

```bash
git clone https://github.com/sgs-97/redis-feature-flags.git
cd redis-feature-flags
```

### Python SDK setup

```bash
cd sdks/python
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### CLI setup

```bash
cd cli
pip install -e ".[dev]"
```

### Java SDK setup

```bash
cd sdks/java
mvn install
```

---

## Running tests

### Python SDK

```bash
cd sdks/python
pytest tests/ -v --cov=redis_feature_flags
```

### Python CLI

```bash
cd cli
pytest tests/ -v
```

### Java SDK

```bash
cd sdks/java
mvn test
```

### E2e tests (requires Redis on port 6399)

```bash
redis-server --port 6399 --daemonize yes
cd sdks/python
pytest tests/e2e/ -v --no-cov
```

---

## Adding a new SDK

Want to add a new language? Here's exactly what to implement:

### Required methods

- `is_enabled(flag_name, user_id, default=False) → bool`
- `create(flag_name, rollout=0, created_by=None) → Flag`
- `enable(flag_name) → void`
- `disable(flag_name) → void`
- `set_rollout(flag_name, percent) → void`
- `add_user(flag_name, user_id) → void`
- `remove_user(flag_name, user_id) → void`
- `create_cohort(cohort_name) → void`
- `add_to_cohort(cohort_name, user_id) → void`
- `list_flags() → List[str]`
- `delete(flag_name) → void`

### Required behavior

Your SDK must pass all tests in `spec/evaluation_spec.json`.

### Key schema

Your SDK must use exactly the key patterns in `spec/schema_spec.json`.

### Reference implementation

See `sdks/python` for the reference implementation.
Every method has a docstring explaining the exact behavior.

### Checklist before opening a PR

- [ ] All spec tests passing
- [ ] 90%+ test coverage
- [ ] README in `sdks/{language}/`
- [ ] Published to package registry (or instructions to do so)

---

## Pull request process

1. Fork the repo
2. Create a branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Run all tests — they must pass
5. Update documentation if needed
6. Update CHANGELOG.md
7. Submit a PR against the `dev` branch — not `master`

---

## Code style

### Python

- Follow PEP 8
- Type hints on all public methods
- Docstrings on all public classes and methods
- Run: `black .` and `isort .` before committing

### Java

- Follow standard Java conventions
- Javadoc on all public classes and methods
- No wildcard imports

---

## Commit message format

```
type: short description

feat:     new feature
fix:      bug fix
docs:     documentation only
test:     adding tests
chore:    maintenance, dependencies
bench:    benchmarks
ci:       CI/CD changes
```

Examples:

```
feat: add TypeScript SDK
fix: handle Redis timeout in evaluator
docs: add Java quickstart to README
test: add e2e tests for cohort expiry
```

---

## Questions

Open a GitHub Discussion or file an issue with the `question` label.