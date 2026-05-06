// FlagNotFoundError.java
package com.redisfeatureflags.exceptions;

public class FlagNotFoundError extends RedisFlagError {
    public FlagNotFoundError(String flagName) {
        super("Flag '" + flagName + "' not found.\n" +
              "Create it with: flags.create(\"" + flagName + "\")");
    }
}