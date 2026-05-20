package featureflags

import (
	"context"
	"strconv"

	"github.com/redis/go-redis/v9"
)

// Evaluator implements the 6-step is_enabled algorithm.
// Evaluates flags against real Redis with local cache fallback.
type Evaluator struct {
	client *redis.Client
	schema *SchemaKeys
	cache  *LocalCache
}

// NewEvaluator creates a new Evaluator.
func NewEvaluator(client *redis.Client, schema *SchemaKeys, cache *LocalCache) *Evaluator {
	return &Evaluator{
		client: client,
		schema: schema,
		cache:  cache,
	}
}

// IsEnabled evaluates a flag for a user in 6 steps.
// Short-circuits at the first answer.
//
// Step 1: Flag exists?              No  → return default
// Step 2: Flag enabled?             No  → return false
// Step 3: Flag expired?             Yes → return false
// Step 4: User in allowlist?        Yes → return true
// Step 5: User in cohort?           Yes → return true
// Step 6: User in rollout bucket?   Yes → true / No → false
func (e *Evaluator) IsEnabled(ctx context.Context, flagName, userID string, defaultValue bool) bool {

	// Step 1 — load flag data
	flagData := e.loadFlag(ctx, flagName)
	if flagData == nil {
		return defaultValue
	}

	// Step 2 — kill switch
	if flagData["enabled"] != "1" {
		return false
	}

	// Step 3 — expiry
	expiresAt := parseInt64(flagData["expires_at"], 0)
	if IsExpired(expiresAt) {
		return false
	}

	// Step 4 — user allowlist
	if e.userInAllowlist(ctx, flagName, userID) {
		return true
	}

	// Step 5 — cohort
	if e.userInCohort(ctx, flagName, userID) {
		return true
	}

	// Step 6 — rollout
	rollout := parseInt(flagData["rollout"], 0)
	return EvaluateRollout(flagName, userID, rollout)
}

// ── Private helpers ────────────────────────────────────────────

func (e *Evaluator) loadFlag(ctx context.Context, flagName string) map[string]string {
	flagKey := e.schema.Flag(flagName)

	// 1. fresh cache
	cached := e.cache.Get(flagKey)
	if cached != nil {
		return cached
	}

	// 2. Redis
	data, err := e.client.HGetAll(ctx, flagKey).Result()
	if err == nil && len(data) > 0 {
		e.cache.Set(flagKey, data)
		return data
	}

	// 3. stale cache fallback
	return e.cache.GetStale(flagKey)
}

func (e *Evaluator) userInAllowlist(ctx context.Context, flagName, userID string) bool {
	result, err := e.client.SIsMember(ctx, e.schema.FlagUsers(flagName), userID).Result()
	if err != nil {
		return false
	}
	return result
}

func (e *Evaluator) userInCohort(ctx context.Context, flagName, userID string) bool {
	result, err := e.client.SInter(ctx,
		e.schema.UserCohorts(userID),
		e.schema.FlagCohorts(flagName),
	).Result()
	if err != nil {
		return false
	}
	return len(result) > 0
}

// ── Parse helpers ──────────────────────────────────────────────

func parseInt(s string, defaultVal int) int {
	if s == "" {
		return defaultVal
	}
	v, err := strconv.Atoi(s)
	if err != nil {
		return defaultVal
	}
	return v
}

func parseInt64(s string, defaultVal int64) int64 {
	if s == "" {
		return defaultVal
	}
	v, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return defaultVal
	}
	return v
}