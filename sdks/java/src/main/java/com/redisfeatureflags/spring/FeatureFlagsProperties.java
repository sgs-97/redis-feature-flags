// FeatureFlagsProperties.java
package com.redisfeatureflags.spring;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "redis-feature-flags")
public class FeatureFlagsProperties {

    private String redisUrl = "redis://localhost:6379";
    private String env = "prod";
    private int cacheTtl = 30;

    public String getRedisUrl() { return redisUrl; }
    public void setRedisUrl(String redisUrl) { this.redisUrl = redisUrl; }

    public String getEnv() { return env; }
    public void setEnv(String env) { this.env = env; }

    public int getCacheTtl() { return cacheTtl; }
    public void setCacheTtl(int cacheTtl) { this.cacheTtl = cacheTtl; }
}