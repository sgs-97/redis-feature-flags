// CohortNotFoundError.java
package com.redisfeatureflags.exceptions;

public class CohortNotFoundError extends RedisFlagError {
    public CohortNotFoundError(String cohortName) {
        super("Cohort '" + cohortName + "' not found.\n" +
              "Create it with: flags.createCohort(\"" + cohortName + "\")");
    }
}