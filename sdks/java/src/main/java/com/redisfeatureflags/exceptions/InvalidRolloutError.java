// InvalidRolloutError.java
package com.redisfeatureflags.exceptions;

public class InvalidRolloutError extends RedisFlagError {
    public InvalidRolloutError(int value) {
        super("Rollout must be between 0 and 100. Got: " + value);
    }
}