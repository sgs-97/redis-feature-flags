// FeatureFlagsAutoConfiguration.java
package com.redisfeatureflags.spring;

import com.redisfeatureflags.FeatureFlags;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import redis.clients.jedis.JedisPool;

@AutoConfiguration
@EnableConfigurationProperties(FeatureFlagsProperties.class)
public class FeatureFlagsAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public JedisPool jedisPool(FeatureFlagsProperties props) {
        return new JedisPool(props.getRedisUrl());
    }

    @Bean
    @ConditionalOnMissingBean
    public FeatureFlags featureFlags(
            JedisPool jedisPool,
            FeatureFlagsProperties props) {
        return new FeatureFlags(
            jedisPool,
            props.getEnv(),
            props.getCacheTtl()
        );
    }
}