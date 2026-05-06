// RedisFlagError.java
package com.redisfeatureflags.exceptions;

public class RedisFlagError extends RuntimeException {
    public RedisFlagError(String message) {
        super(message);
    }
}