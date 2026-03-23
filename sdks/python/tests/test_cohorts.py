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
    """
    Given: cohort name beta-testers.
    After: create() is called.
    Expected: exists() returns True — cohort is registered in the index.
    """
    cohorts.create("beta-testers")
    assert cohorts.exists("beta-testers") is True


def test_delete_cohort(cohorts, redis_client, schema):
    """
    Given: cohort beta-testers created then deleted.
    Expected: exists() returns False — cohort removed from index.
    """
    cohorts.create("beta-testers")
    cohorts.delete("beta-testers")
    assert cohorts.exists("beta-testers") is False


def test_add_user_to_cohort(cohorts, redis_client, schema):
    """
    Given: alice added to cohort beta-testers.
    Expected: alice appears in get_members() result.
    """
    cohorts.create("beta-testers")
    cohorts.add_user("beta-testers", "alice")
    assert "alice" in cohorts.get_members("beta-testers")


def test_add_user_updates_reverse_index(cohorts, redis_client, schema):
    """
    Given: alice added to cohort beta-testers.
    Expected: reverse index key user:alice:cohorts contains beta-testers.
              Both directions of the bidirectional index must stay in sync.
    """
    cohorts.add_user("beta-testers", "alice")
    members = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" in members


def test_remove_user_from_cohort(cohorts, redis_client, schema):
    """
    Given: alice added then removed from cohort beta-testers.
    Expected: alice no longer appears in get_members() result.
    """
    cohorts.add_user("beta-testers", "alice")
    cohorts.remove_user("beta-testers", "alice")
    assert "alice" not in cohorts.get_members("beta-testers")


def test_remove_user_updates_reverse_index(cohorts, redis_client, schema):
    """
    Given: alice added then removed from cohort beta-testers.
    Expected: reverse index key user:alice:cohorts no longer contains beta-testers.
              Both directions of the bidirectional index must stay in sync.
    """
    cohorts.add_user("beta-testers", "alice")
    cohorts.remove_user("beta-testers", "alice")
    members = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" not in members


def test_get_members_empty(cohorts):
    """
    Given: cohort that was never created or has no members.
    Expected: get_members() returns empty set — no error raised.
    """
    assert cohorts.get_members("nonexistent") == set()


def test_list_cohorts(cohorts):
    """
    Given: two cohorts created — beta-testers and premium-users.
    Expected: list_cohorts() returns both names.
              Uses the cohorts index Set — no KEYS * scan needed.
    """
    cohorts.create("beta-testers")
    cohorts.create("premium-users")
    result = cohorts.list_cohorts()
    assert "beta-testers" in result
    assert "premium-users" in result


def test_exists_false_for_nonexistent(cohorts):
    """
    Given: cohort that was never created.
    Expected: exists() returns False.
    """
    assert cohorts.exists("nonexistent") is False


def test_user_in_multiple_cohorts(cohorts, redis_client, schema):
    """
    Given: alice added to both beta-testers and premium-users cohorts.
    Expected: reverse index for alice contains both cohort names.
              A user can belong to multiple cohorts simultaneously.
    """
    cohorts.add_user("beta-testers", "alice")
    cohorts.add_user("premium-users", "alice")
    members = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" in members
    assert b"premium-users" in members

def test_delete_cohort_cleans_members_set(cohorts, redis_client, schema):
    """
    Given: cohort beta-testers with alice and bob as members.
    After: delete() is called.
    Expected: ff:{env}:cohort:beta-testers Set no longer exists in Redis.
              Members are fully removed — not just the index entry.
    """
    cohorts.add_user("beta-testers", "alice")
    cohorts.add_user("beta-testers", "bob")
    cohorts.delete("beta-testers")
    assert cohorts.get_members("beta-testers") == set()


def test_delete_cohort_cleans_user_reverse_index(cohorts, redis_client, schema):
    """
    Given: alice is in beta-testers cohort.
    After: beta-testers cohort is deleted.
    Expected: alice's reverse index no longer contains beta-testers.
              Stale data is cleaned up — not left behind.
    """
    cohorts.add_user("beta-testers", "alice")
    cohorts.delete("beta-testers")
    members = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" not in members


def test_delete_cohort_cleans_all_members_reverse_index(cohorts, redis_client, schema):
    """
    Given: beta-testers cohort with alice, bob, and charlie as members.
    After: beta-testers cohort is deleted.
    Expected: all three users' reverse index keys no longer contain beta-testers.
              Every member's reverse index is cleaned — not just the first one.
    """
    cohorts.add_user("beta-testers", "alice")
    cohorts.add_user("beta-testers", "bob")
    cohorts.add_user("beta-testers", "charlie")
    cohorts.delete("beta-testers")
    for user in ["alice", "bob", "charlie"]:
        members = redis_client.smembers(schema.user_cohorts(user))
        assert b"beta-testers" not in members


def test_delete_cohort_preserves_other_cohorts_in_reverse_index(cohorts, redis_client, schema):
    """
    Given: alice is in both beta-testers and premium-users cohorts.
    After: beta-testers cohort is deleted.
    Expected: alice's reverse index still contains premium-users.
              Deleting one cohort does not affect membership in other cohorts.
    """
    cohorts.add_user("beta-testers", "alice")
    cohorts.add_user("premium-users", "alice")
    cohorts.delete("beta-testers")
    members = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" not in members
    assert b"premium-users" in members


def test_delete_empty_cohort_no_error(cohorts, redis_client, schema):
    """
    Given: cohort beta-testers created but no members added.
    After: delete() is called.
    Expected: no error raised — deleting an empty cohort is safe.
    """
    cohorts.create("beta-testers")
    cohorts.delete("beta-testers")
    assert cohorts.exists("beta-testers") is False


def test_delete_cohort_removes_from_index(cohorts, redis_client, schema):
    """
    Given: two cohorts created — beta-testers and premium-users.
    After: beta-testers deleted.
    Expected: list_cohorts() no longer contains beta-testers
              but still contains premium-users.
    """
    cohorts.create("beta-testers")
    cohorts.create("premium-users")
    cohorts.delete("beta-testers")
    result = cohorts.list_cohorts()
    assert "beta-testers" not in result
    assert "premium-users" in result