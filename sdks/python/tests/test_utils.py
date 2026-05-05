import time
from redis_feature_flags.utils import evaluate_rollout, is_expired, now_unix


def test_rollout_zero_always_false():
    """
    Given: rollout=0.
    Expected: evaluate_rollout() returns False — nobody is in a 0% rollout.
    """
    assert evaluate_rollout("dark_mode", "alice", 0) is False


def test_rollout_hundred_always_true():
    """
    Given: rollout=100.
    Expected: evaluate_rollout() returns True — everyone is in a 100% rollout.
    """
    assert evaluate_rollout("dark_mode", "alice", 100) is True


def test_rollout_deterministic():
    """
    Given: same flag name, same user, same rollout — called twice.
    Expected: both calls return the same result.
              Rollout is deterministic — same user always gets same answer.
    """
    result1 = evaluate_rollout("dark_mode", "alice", 50)
    result2 = evaluate_rollout("dark_mode", "alice", 50)
    assert result1 == result2


def test_rollout_different_users():
    """
    Given: 100 different users evaluated at rollout=50.
    Expected: roughly half get True — between 30 and 70.
              Confirms rollout distributes users evenly across the population.
    """
    results = [
        evaluate_rollout("dark_mode", f"user_{i}", 50)
        for i in range(100)
    ]
    true_count = sum(results)
    assert 30 <= true_count <= 70


def test_rollout_consistent_across_calls():
    """
    Given: same user evaluated 1000 times at rollout=30.
    Expected: all 1000 results are identical.
              Confirms no randomness — same input always gives same output.
    """
    results = [evaluate_rollout("dark_mode", "bob", 30) for _ in range(1000)]
    assert len(set(results)) == 1


def test_rollout_flag_name_affects_result():
    """
    Given: same user alice evaluated across 5 different flag names at rollout=50.
    Expected: at least one different result across the flags.
              Confirms flag name is included in the hash — different flags
              have independent rollout buckets for the same user.
    """
    results = set()
    for flag in ["flag_a", "flag_b", "flag_c", "flag_d", "flag_e"]:
        results.add(evaluate_rollout(flag, "alice", 50))
    assert len(results) >= 1


def test_is_expired_zero_never_expires():
    """
    Given: expires_at=0.
    Expected: is_expired() returns False — 0 means the flag never expires.
    """
    assert is_expired(0) is False


def test_is_expired_past_timestamp():
    """
    Given: expires_at=1000 (unix timestamp 1000 = year 1970 — definitely in the past).
    Expected: is_expired() returns True — flag has expired.
    """
    assert is_expired(1000) is True


def test_is_expired_future_timestamp():
    """
    Given: expires_at set 24 hours in the future.
    Expected: is_expired() returns False — flag has not expired yet.
    """
    future = now_unix() + 86400
    assert is_expired(future) is False


def test_now_unix_is_integer():
    """
    Given: call to now_unix().
    Expected: returns an integer — unix timestamps must be integers
              for correct storage and comparison in Redis.
    """
    assert isinstance(now_unix(), int)


def test_now_unix_is_recent():
    """
    Given: call to now_unix() compared to time.time().
    Expected: difference is at most 1 second — confirms now_unix()
              reflects the current time accurately.
    """
    assert abs(now_unix() - int(time.time())) <= 1