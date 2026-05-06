// SchemaVersionError.java
package com.redisfeatureflags.exceptions;

public class SchemaVersionError extends RedisFlagError {
    public SchemaVersionError(String expected, String found) {
        super("Schema version mismatch. " +
              "SDK supports version " + expected + ", " +
              "Redis has version " + found + ". " +
              "Please upgrade redis-feature-flags.");
    }
}