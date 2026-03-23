from __future__ import annotations

import redis

from .exceptions import CohortNotFoundError
from .schema import SchemaKeys


class CohortManager:
    """
    Manages cohorts in Redis.

    A cohort is a named group of users — e.g. beta-testers, premium-users.
    Flags can target entire cohorts instead of individual users.

    Uses a bidirectional index:
      Direction 1 — ff:{env}:cohort:{name}        → Set of user_ids
      Direction 2 — ff:{env}:user:{id}:cohorts    → Set of cohort names

    Direction 1 answers: "who is in this cohort?" (management)
    Direction 2 answers: "which cohorts does this user belong to?" (evaluation)
    Both directions must always stay in sync.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        schema: SchemaKeys,
    ):
        self._redis = redis_client
        self._schema = schema

    def create(self, cohort_name: str) -> None:
        """
        Register a cohort name in the cohorts index.

        Adds cohort_name to ff:{env}:cohorts:__index__ so it
        appears in list_cohorts() without needing a KEYS * scan.
        Does not add any members — cohort starts empty.
        """
        self._redis.sadd(self._schema.cohorts_index(), cohort_name)

    def delete(self, cohort_name: str) -> None:
        """
        Fully remove a cohort from Redis — cleans up all three locations.

        Step 1 — get all members before deleting
                so we can clean their reverse index keys.

        Step 2 — pipeline all removals atomically:
            a. Remove cohort name from every member's reverse index
            ff:{env}:user:{user_id}:cohorts
            b. Delete the cohort members Set
            ff:{env}:cohort:{name}
            c. Remove cohort name from the cohorts index
            ff:{env}:cohorts:__index__

        Note: does NOT clean up flag cohort Sets that reference this cohort.
            ff:{env}:flag:{name}:cohorts may still contain this cohort name.
            Evaluation is unaffected — SINTER finds no match once the cohort
            is gone from the user reverse index.
            Full flag cleanup is planned for v2.
        """
        members = self._redis.smembers(self._schema.cohort(cohort_name))

        pipe = self._redis.pipeline()
        for member in members:
            pipe.srem(self._schema.user_cohorts(member.decode()), cohort_name)
        pipe.delete(self._schema.cohort(cohort_name))
        pipe.srem(self._schema.cohorts_index(), cohort_name)
        pipe.execute()

    def add_user(self, cohort_name: str, user_id: str) -> None:
        """
        Add a user to a cohort — writes both directions atomically.

        Uses a Redis pipeline to send both commands in one round trip
        and execute them together — either both succeed or both fail.

        Line 1 — direction 1 (cohort → members):
            SADD ff:{env}:cohort:{name} {user_id}

        Line 2 — direction 2 (user → cohorts) reverse index:
            SADD ff:{env}:user:{user_id}:cohorts {cohort_name}

        Direction 2 is what makes evaluation fast — SINTER can find
        cohort matches in one Redis call instead of checking each cohort.
        """
        pipe = self._redis.pipeline()
        pipe.sadd(self._schema.cohort(cohort_name), user_id)
        pipe.sadd(self._schema.user_cohorts(user_id), cohort_name)
        pipe.execute()

    def remove_user(self, cohort_name: str, user_id: str) -> None:
        """
        Remove a user from a cohort — removes both directions atomically.

        Uses a Redis pipeline — both removals happen together.

        Line 1 — removes user from cohort members Set:
            SREM ff:{env}:cohort:{name} {user_id}

        Line 2 — removes cohort from user's reverse index:
            SREM ff:{env}:user:{user_id}:cohorts {cohort_name}

        Both directions must be removed to keep the index consistent.
        """
        pipe = self._redis.pipeline()
        pipe.srem(self._schema.cohort(cohort_name), user_id)
        pipe.srem(self._schema.user_cohorts(user_id), cohort_name)
        pipe.execute()

    def get_members(self, cohort_name: str) -> set:
        """
        Return all user_ids in a cohort as a Python set of strings.

        Reads from direction 1 — ff:{env}:cohort:{name}.
        Redis returns bytes — decoded to strings before returning.
        Returns empty set if cohort does not exist.

        Used for management — e.g. CLI command "show me who is in beta-testers".
        Not used during flag evaluation — direction 2 is used there instead.
        """
        members = self._redis.smembers(self._schema.cohort(cohort_name))
        return {m.decode() for m in members}

    def list_cohorts(self) -> list:
        """
        Return all cohort names as a Python list of strings.

        Reads from ff:{env}:cohorts:__index__ — the cohort name registry.
        Redis returns bytes — decoded to strings before returning.

        Safe to call in production — reads one Set key, no KEYS * scan.
        """
        cohorts = self._redis.smembers(self._schema.cohorts_index())
        return [c.decode() for c in cohorts]

    def exists(self, cohort_name: str) -> bool:
        """
        Check if a cohort name is registered in the index.

        Uses SISMEMBER on ff:{env}:cohorts:__index__ — O(1) lookup.
        Returns True if cohort exists, False otherwise.

        Note: a cohort can exist in the index but have zero members.
        exists() only checks registration — not whether it has members.
        """
        return bool(
            self._redis.sismember(
                self._schema.cohorts_index(), cohort_name
            )
        )