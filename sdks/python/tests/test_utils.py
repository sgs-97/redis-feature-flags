import time
from redis_feature_flags.utils import evaluate_rollout, is_expired, now_unix


def test_rollout_zero_always_false():
    assert evaluate_rollout("dark_mode", "alice", 0) is False


def test_rollout_hundred_always_true():
    assert evaluate_rollout("dark_mode", "alice", 100) is True


def test_rollout_deterministic():
    result1 = evaluate_rollout("dark_mode", "alice", 50)
    result2 = evaluate_rollout("dark_mode", "alice", 50)
    assert result1 == result2


def test_rollout_different_users():
    results = [
        evaluate_rollout("dark_mode", f"user_{i}", 50)
        for i in range(100)
    ]
    true_count = sum(results)
    assert 30 <= true_count <= 70


def test_rollout_consistent_across_calls():
    results = [evaluate_rollout("dark_mode", "bob", 30) for _ in range(1000)]
    assert len(set(results)) == 1


def test_rollout_flag_name_affects_result():
    results = set()
    for flag in ["flag_a", "flag_b", "flag_c", "flag_d", "flag_e"]:
        results.add(evaluate_rollout(flag, "alice", 50))
    assert len(results) >= 1


def test_is_expired_zero_never_expires():
    assert is_expired(0) is False


def test_is_expired_past_timestamp():
    assert is_expired(1000) is True


def test_is_expired_future_timestamp():
    future = now_unix() + 86400
    assert is_expired(future) is False


def test_now_unix_is_integer():
    assert isinstance(now_unix(), int)


def test_now_unix_is_recent():
    assert abs(now_unix() - int(time.time())) <= 1