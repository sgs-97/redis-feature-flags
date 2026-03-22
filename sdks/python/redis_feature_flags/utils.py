from __future__ import annotations

import hashlib
import time


def evaluate_rollout(flag_name: str, user_id: str, rollout: int) -> bool:
    if rollout <= 0:
        return False
    if rollout >= 100:
        return True
    key = f"{flag_name}:{user_id}"
    hash_hex = hashlib.sha256(key.encode()).hexdigest()
    bucket = int(hash_hex[:8], 16) % 100
    return bucket < rollout


def now_unix() -> int:
    return int(time.time())


def is_expired(expires_at: int) -> bool:
    if expires_at == 0:
        return False
    return now_unix() > expires_at