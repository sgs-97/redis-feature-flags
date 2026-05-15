## Description

What does this PR do? Why?

---

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] New SDK
- [ ] Documentation
- [ ] Tests
- [ ] Chore / maintenance

---

## Changes made

- 
- 
- 

---

## Testing

- [ ] All existing tests pass
- [ ] New tests added for new code
- [ ] E2e tests pass against real Redis
- [ ] Test coverage ≥ 90%

Run tests:

```bash
# Python SDK
cd sdks/python
pytest tests/ -v --cov=redis_feature_flags

# Python CLI
cd cli
pytest tests/ -v

# Java SDK
cd sdks/java
mvn test
```

---

## Documentation

- [ ] README updated if needed
- [ ] docs/docs.md updated if needed
- [ ] CHANGELOG.md updated
- [ ] Docstrings added for new public methods

---

## New SDK checklist (skip if not adding a new SDK)

- [ ] All spec tests in `spec/evaluation_spec.json` pass
- [ ] Same Redis key schema as Python SDK
- [ ] 90%+ test coverage
- [ ] README in `sdks/{language}/`
- [ ] Published to package registry or instructions included

---

## Related issues

Closes #