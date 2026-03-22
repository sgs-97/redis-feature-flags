# sdks/python/redis_feature_flags/evaluator.py

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import redis

from .cache import LocalCache
from .exceptions import FlagNotFoundError, RedisConnectionError
from .schema import SchemaKeys
from .utils import evaluate_rollout, is_expired, now_unix

if TYPE_CHECKING:
    pass


class Evaluator:
    """
    Core flag evaluation engine.

    Evaluates is_enabled() using this order:
      1. Check local cache first
      2. Fetch from Redis if cache miss
      3. Fall back to stale cache if Redis is down
      4. Fall back to default if nothing available

    Evaluation steps (once flag data is loaded):
      1. Flag exists?         → no  → return default
      2. Flag enabled?        → no  → return False
      3. Flag expired?        → yes → return False
      4. User in allowlist?   → yes → return True
      5. User in cohort?      → yes → return True
      6. User in rollout?     → yes → return True
                                no  → return False
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        schema: SchemaKeys,
        cache: LocalCache,
    ):
        self._redis = redis_client
        self._schema = schema
        self._cache = cache

    def is_enabled(
        self,
        flag_name: str,
        user_id: str,
        default: bool = False,
    ) -> bool:
        """
        Evaluate a flag for a given user.

        Args:
            flag_name:  Name of the flag e.g. "dark_mode"
            user_id:    User to evaluate for e.g. "alice"
            default:    Return value when flag missing or
                        Redis unreachable. Default False.

        Returns:
            True if the user should get this feature.
            False otherwise.
        """
        flag_key = self._schema.flag(flag_name)

        # ── Step 1: Load flag data ─────────────────────────
        flag_data = self._load_flag(flag_key, default)
        if flag_data is None:
            return default

        # ── Step 2: Kill switch ────────────────────────────
        if flag_data.get("enabled", "0") != "1":
            return False

        # ── Step 3: Expiry check ───────────────────────────
        expires_at = int(flag_data.get("expires_at", "0") or "0")
        if is_expired(expires_at):
            return False

        # ── Step 4: User allowlist ─────────────────────────
        if self._user_in_allowlist(flag_name, user_id):
            return True

        # ── Step 5: Cohort check ───────────────────────────
        if self._user_in_cohort(flag_name, user_id):
            return True

        # ── Step 6: Rollout ────────────────────────────────
        rollout = int(flag_data.get("rollout", "0") or "0")
        return evaluate_rollout(flag_name, user_id, rollout)

    # ── Private helpers ────────────────────────────────────

    def _load_flag(
        self,
        flag_key: str,
        default: bool,
    ) -> dict | None:
        """
        Load flag data with cache → Redis → stale cache fallback.
        Returns None if flag does not exist anywhere.
        """
        # 1. Try fresh cache
        cached = self._cache.get(flag_key)
        if cached is not None:
            return cached

        # 2. Try Redis
        try:
            data = self._redis.hgetall(flag_key)
            if not data:
                return None
            # Redis returns bytes — decode to strings
            decoded = {
                k.decode(): v.decode()
                for k, v in data.items()
            }
            self._cache.set(flag_key, decoded)
            return decoded

        except redis.RedisError:
            # 3. Redis down — try stale cache
            stale = self._cache.get_stale(flag_key)
            if stale is not None:
                return stale
            return None

    def _user_in_allowlist(self, flag_name: str, user_id: str) -> bool:
        """Check if user is in the flag's user allowlist."""
        key = self._schema.flag_users(flag_name)
        try:
            return bool(self._redis.sismember(key, user_id))
        except redis.RedisError:
            return False

    def _user_in_cohort(self, flag_name: str, user_id: str) -> bool:
        """
        Check if user belongs to any cohort the flag allows.
        Uses SINTER — one Redis call regardless of cohort count.
        """
        user_cohorts_key = self._schema.user_cohorts(user_id)
        flag_cohorts_key = self._schema.flag_cohorts(flag_name)
        try:
            intersection = self._redis.sinter(
                user_cohorts_key,
                flag_cohorts_key,
            )
            return len(intersection) > 0
        except redis.RedisError:
            return False