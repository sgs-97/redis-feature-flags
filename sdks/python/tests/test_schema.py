from redis_feature_flags.schema import SchemaKeys


def test_flag_key():
    """
    Given: SchemaKeys with env=prod and flag name dark_mode.
    Expected: flag() returns ff:prod:flag:dark_mode.
    """
    keys = SchemaKeys(env="prod")
    assert keys.flag("dark_mode") == "ff:prod:flag:dark_mode"


def test_flag_users_key():
    """
    Given: SchemaKeys with env=prod and flag name dark_mode.
    Expected: flag_users() returns ff:prod:flag:dark_mode:users.
    """
    keys = SchemaKeys(env="prod")
    assert keys.flag_users("dark_mode") == "ff:prod:flag:dark_mode:users"


def test_flag_cohorts_key():
    """
    Given: SchemaKeys with env=prod and flag name dark_mode.
    Expected: flag_cohorts() returns ff:prod:flag:dark_mode:cohorts.
    """
    keys = SchemaKeys(env="prod")
    assert keys.flag_cohorts("dark_mode") == "ff:prod:flag:dark_mode:cohorts"


def test_flag_history_key():
    """
    Given: SchemaKeys with env=prod and flag name dark_mode.
    Expected: flag_history() returns ff:prod:flag:dark_mode:history.
    """
    keys = SchemaKeys(env="prod")
    assert keys.flag_history("dark_mode") == "ff:prod:flag:dark_mode:history"


def test_cohort_key():
    """
    Given: SchemaKeys with env=prod and cohort name beta-testers.
    Expected: cohort() returns ff:prod:cohort:beta-testers.
    """
    keys = SchemaKeys(env="prod")
    assert keys.cohort("beta-testers") == "ff:prod:cohort:beta-testers"


def test_user_cohorts_key():
    """
    Given: SchemaKeys with env=prod and user id alice.
    Expected: user_cohorts() returns ff:prod:user:alice:cohorts.
    """
    keys = SchemaKeys(env="prod")
    assert keys.user_cohorts("alice") == "ff:prod:user:alice:cohorts"


def test_flags_index_key():
    """
    Given: SchemaKeys with env=prod.
    Expected: flags_index() returns ff:prod:flag:__index__.
              This key holds the names of all flags — avoids KEYS * scan.
    """
    keys = SchemaKeys(env="prod")
    assert keys.flags_index() == "ff:prod:flag:__index__"


def test_cohorts_index_key():
    """
    Given: SchemaKeys with env=prod.
    Expected: cohorts_index() returns ff:prod:cohorts:__index__.
              This key holds the names of all cohorts — avoids KEYS * scan.
    """
    keys = SchemaKeys(env="prod")
    assert keys.cohorts_index() == "ff:prod:cohorts:__index__"


def test_schema_version_key():
    """
    Given: SchemaKeys with env=prod.
    Expected: schema_version() returns ff:prod:__schema__.
              SDKs check this on startup to detect breaking schema changes.
    """
    keys = SchemaKeys(env="prod")
    assert keys.schema_version() == "ff:prod:__schema__"


def test_different_environments():
    """
    Given: two SchemaKeys instances — one for prod, one for staging.
    Expected: same flag name produces different keys per environment.
              Prod and staging can share one Redis instance without collision.
    """
    prod = SchemaKeys(env="prod")
    staging = SchemaKeys(env="staging")
    assert prod.flag("dark_mode") != staging.flag("dark_mode")
    assert prod.flag("dark_mode") == "ff:prod:flag:dark_mode"
    assert staging.flag("dark_mode") == "ff:staging:flag:dark_mode"