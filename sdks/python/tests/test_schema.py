from redis_feature_flags.schema import SchemaKeys


def test_flag_key():
    keys = SchemaKeys(env="prod")
    assert keys.flag("dark_mode") == "ff:prod:flag:dark_mode"


def test_flag_users_key():
    keys = SchemaKeys(env="prod")
    assert keys.flag_users("dark_mode") == "ff:prod:flag:dark_mode:users"


def test_flag_cohorts_key():
    keys = SchemaKeys(env="prod")
    assert keys.flag_cohorts("dark_mode") == "ff:prod:flag:dark_mode:cohorts"


def test_flag_history_key():
    keys = SchemaKeys(env="prod")
    assert keys.flag_history("dark_mode") == "ff:prod:flag:dark_mode:history"


def test_cohort_key():
    keys = SchemaKeys(env="prod")
    assert keys.cohort("beta-testers") == "ff:prod:cohort:beta-testers"


def test_user_cohorts_key():
    keys = SchemaKeys(env="prod")
    assert keys.user_cohorts("alice") == "ff:prod:user:alice:cohorts"


def test_flags_index_key():
    keys = SchemaKeys(env="prod")
    assert keys.flags_index() == "ff:prod:flags:__index__"


def test_cohorts_index_key():
    keys = SchemaKeys(env="prod")
    assert keys.cohorts_index() == "ff:prod:cohorts:__index__"


def test_schema_version_key():
    keys = SchemaKeys(env="prod")
    assert keys.schema_version() == "ff:prod:__schema__"


def test_different_environments():
    prod = SchemaKeys(env="prod")
    staging = SchemaKeys(env="staging")
    assert prod.flag("dark_mode") != staging.flag("dark_mode")
    assert prod.flag("dark_mode") == "ff:prod:flag:dark_mode"
    assert staging.flag("dark_mode") == "ff:staging:flag:dark_mode"