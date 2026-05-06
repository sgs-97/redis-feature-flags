package com.redisfeatureflags;

import redis.clients.jedis.Jedis;

@FunctionalInterface
public interface JedisProvider {
    Jedis getResource();
}