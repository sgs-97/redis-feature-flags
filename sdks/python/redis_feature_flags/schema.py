class SchemaKeys:
    def __init__(self, env: str = "prod"):
        self.env = env
        self._prefix = f"ff:{env}"

    def flag(self, flag_name: str) -> str:
        return f"{self._prefix}:flag:{flag_name}"

    def flag_users(self, flag_name: str) -> str:
        return f"{self._prefix}:flag:{flag_name}:users"

    def flag_cohorts(self, flag_name: str) -> str:
        return f"{self._prefix}:flag:{flag_name}:cohorts"

    def flag_history(self, flag_name: str) -> str:
        return f"{self._prefix}:flag:{flag_name}:history"

    def cohort(self, cohort_name: str) -> str:
        return f"{self._prefix}:cohort:{cohort_name}"

    def user_cohorts(self, user_id: str) -> str:
        return f"{self._prefix}:user:{user_id}:cohorts"

    def flags_index(self) -> str:
        return f"{self._prefix}:flags:__index__"

    def cohorts_index(self) -> str:
        return f"{self._prefix}:cohorts:__index__"

    def schema_version(self) -> str:
        return f"{self._prefix}:__schema__"