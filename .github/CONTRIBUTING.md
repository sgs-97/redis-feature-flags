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
Your SDK must pass all tests in /spec/evaluation_spec.json

### Key schema
Your SDK must use exactly the key patterns in /spec/schema_spec.json

### Reference implementation
See /sdks/python for the reference implementation.
Every method has a docstring explaining the exact behavior.

### Checklist before opening a PR
- [ ] All spec tests passing
- [ ] 90%+ test coverage
- [ ] README in sdks/{language}/
- [ ] Published to package registry (or instructions to do so)