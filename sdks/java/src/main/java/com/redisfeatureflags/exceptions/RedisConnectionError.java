// RedisConnectionError.java
package com.redisfeatureflags.exceptions;

public class RedisConnectionError extends RedisFlagError {
    public RedisConnectionError(String message) {
        super(message);
    }
}