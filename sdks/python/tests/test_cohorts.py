import pytest
import fakeredis

from redis_feature_flags.cohorts import CohortManager
from redis_feature_flags.schema import SchemaKeys


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis()


@pytest.fixture
def schema():
    return SchemaKeys(env="test")


@pytest.fixture
def cohorts(redis_client, schema):
    return CohortManager(redis_client, schema)


def test_create_cohort(cohorts, redis_client, schema):
    cohorts.create("beta-testers")
    assert cohorts.exists("beta-testers") is True


def test_delete_cohort(cohorts, redis_client, schema):
    cohorts.create("beta-testers")
    cohorts.delete("beta-testers")
    assert cohorts.exists("beta-testers") is False


def test_add_user_to_cohort(cohorts, redis_client, schema):
    cohorts.create("beta-testers")
    cohorts.add_user("beta-testers", "alice")
    assert "alice" in cohorts.get_members("beta-testers")


def test_add_user_updates_reverse_index(cohorts, redis_client, schema):
    cohorts.add_user("beta-testers", "alice")
    members = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" in members


def test_remove_user_from_cohort(cohorts, redis_client, schema):
    cohorts.add_user("beta-testers", "alice")
    cohorts.remove_user("beta-testers", "alice")
    assert "alice" not in cohorts.get_members("beta-testers")


def test_remove_user_updates_reverse_index(cohorts, redis_client, schema):
    cohorts.add_user("beta-testers", "alice")
    cohorts.remove_user("beta-testers", "alice")
    members = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" not in members


def test_get_members_empty(cohorts):
    assert cohorts.get_members("nonexistent") == set()


def test_list_cohorts(cohorts):
    cohorts.create("beta-testers")
    cohorts.create("premium-users")
    result = cohorts.list_cohorts()
    assert "beta-testers" in result
    assert "premium-users" in result


def test_exists_false_for_nonexistent(cohorts):
    assert cohorts.exists("nonexistent") is False


def test_user_in_multiple_cohorts(cohorts, redis_client, schema):
    cohorts.add_user("beta-testers", "alice")
    cohorts.add_user("premium-users", "alice")
    members = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" in members
    assert b"premium-users" in members