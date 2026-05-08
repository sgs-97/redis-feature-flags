package com.redisfeatureflags;

public class SchemaKeys {

    private final String env;
    private final String prefix;

    public SchemaKeys(String env) {
        this.env = env;
        this.prefix = "ff:" + env;
    }

    public String getEnv() {
        return env;
    }

    public String flag(String flagName) {
        return prefix + ":flag:" + flagName;
    }

    public String flagUsers(String flagName) {
        return prefix + ":flag:" + flagName + ":users";
    }

    public String flagCohorts(String flagName) {
        return prefix + ":flag:" + flagName + ":cohorts";
    }

    public String flagHistory(String flagName) {
        return prefix + ":flag:" + flagName + ":history";
    }

    public String cohort(String cohortName) {
        return prefix + ":cohort:" + cohortName;
    }

    public String userCohorts(String userId) {
        return prefix + ":user:" + userId + ":cohorts";
    }

    public String flagsIndex() {
        return prefix + ":flag:__index__";
    }

    public String cohortsIndex() {
        return prefix + ":cohorts:__index__";
    }

    public String schemaVersion() {
        return prefix + ":__schema__";
    }
}