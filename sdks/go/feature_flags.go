package featureflags

import (
	"context"
	"fmt"
	"sort"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

// FeatureFlags is the main public API.
// Connect to your Redis and start evaluating flags.
//
//	client := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
//	flags := featureflags.New(client, "prod")
//	enabled, err := flags.IsEnabled(ctx, "dark_mode", "alice")
type FeatureFlags struct {
	client    *redis.Client
	schema    *SchemaKeys
	cache     *LocalCache
	evaluator *Evaluator
	cohorts   *CohortManager
}

// New creates a new FeatureFlags with default cache TTL of 30 seconds.
func New(client *redis.Client, env string) *FeatureFlags {
	return NewWithTTL(client, env, 30)
}

// NewWithTTL creates a new FeatureFlags with custom cache TTL in seconds.
func NewWithTTL(client *redis.Client, env string, cacheTTLSeconds int) *FeatureFlags {
	schema := NewSchemaKeys(env)
	cache := NewLocalCache(cacheTTLSeconds)
	return &FeatureFlags{
		client:    client,
		schema:    schema,
		cache:     cache,
		evaluator: NewEvaluator(client, schema, cache),
		cohorts:   NewCohortManager(client, schema),
	}
}

// ── Core evaluation ────────────────────────────────────────────

// IsEnabled evaluates a flag for a user.
// Returns (true, nil) if user gets the flag.
// Returns (false, nil) if user does not get the flag.
// Returns (defaultValue, nil) if flag does not exist or Redis is down.
func (f *FeatureFlags) IsEnabled(ctx context.Context, flagName, userID string) (bool, error) {
	return f.evaluator.IsEnabled(ctx, flagName, userID, false), nil
}

// IsEnabledWithDefault evaluates a flag with a custom default value.
func (f *FeatureFlags) IsEnabledWithDefault(ctx context.Context, flagName, userID string, defaultValue bool) (bool, error) {
	return f.evaluator.IsEnabled(ctx, flagName, userID, defaultValue), nil
}

// ── Flag management ────────────────────────────────────────────

// Create creates a new flag. Disabled by default.
func (f *FeatureFlags) Create(ctx context.Context, flagName string, rollout int, createdBy string) error {
	if rollout < 0 || rollout > 100 {
		return &InvalidRolloutError{Value: rollout}
	}

	now := strconv.FormatInt(NowUnix(), 10)
	fields := map[string]string{
		"enabled":      "0",
		"rollout":      strconv.Itoa(rollout),
		"expires_at":   "0",
		"created_at":   now,
		"updated_at":   now,
		"created_by":   createdBy,
		"updated_by":   createdBy,
		"flag_version": "1",
	}

	pipe := f.client.Pipeline()
	pipe.HSet(ctx, f.schema.Flag(flagName), fields)
	pipe.SAdd(ctx, f.schema.FlagsIndex(), flagName)
	_, err := pipe.Exec(ctx)
	return err
}

// Enable enables a flag.
func (f *FeatureFlags) Enable(ctx context.Context, flagName, updatedBy string) error {
	if err := f.assertExists(ctx, flagName); err != nil {
		return err
	}
	err := f.client.HSet(ctx, f.schema.Flag(flagName), map[string]string{
		"enabled":    "1",
		"updated_at": strconv.FormatInt(NowUnix(), 10),
		"updated_by": updatedBy,
	}).Err()
	if err != nil {
		return err
	}
	f.cache.Delete(f.schema.Flag(flagName))
	return nil
}

// Disable disables a flag instantly. Kill switch.
func (f *FeatureFlags) Disable(ctx context.Context, flagName, updatedBy string) error {
	if err := f.assertExists(ctx, flagName); err != nil {
		return err
	}
	err := f.client.HSet(ctx, f.schema.Flag(flagName), map[string]string{
		"enabled":    "0",
		"updated_at": strconv.FormatInt(NowUnix(), 10),
		"updated_by": updatedBy,
	}).Err()
	if err != nil {
		return err
	}
	f.cache.Delete(f.schema.Flag(flagName))
	return nil
}

// SetRollout updates rollout percentage.
func (f *FeatureFlags) SetRollout(ctx context.Context, flagName string, percent int, updatedBy string) error {
	if percent < 0 || percent > 100 {
		return &InvalidRolloutError{Value: percent}
	}
	if err := f.assertExists(ctx, flagName); err != nil {
		return err
	}
	err := f.client.HSet(ctx, f.schema.Flag(flagName), map[string]string{
		"rollout":    strconv.Itoa(percent),
		"updated_at": strconv.FormatInt(NowUnix(), 10),
		"updated_by": updatedBy,
	}).Err()
	if err != nil {
		return err
	}
	f.cache.Delete(f.schema.Flag(flagName))
	return nil
}

// Delete permanently deletes a flag and all associated data.
func (f *FeatureFlags) Delete(ctx context.Context, flagName string) error {
	pipe := f.client.Pipeline()
	pipe.Del(ctx, f.schema.Flag(flagName))
	pipe.Del(ctx, f.schema.FlagUsers(flagName))
	pipe.Del(ctx, f.schema.FlagCohorts(flagName))
	pipe.Del(ctx, f.schema.FlagHistory(flagName))
	pipe.SRem(ctx, f.schema.FlagsIndex(), flagName)
	_, err := pipe.Exec(ctx)
	if err != nil {
		return err
	}
	f.cache.Delete(f.schema.Flag(flagName))
	return nil
}

// Get returns all flag fields as a map.
func (f *FeatureFlags) Get(ctx context.Context, flagName string) (map[string]string, error) {
	if err := f.assertExists(ctx, flagName); err != nil {
		return nil, err
	}
	return f.client.HGetAll(ctx, f.schema.Flag(flagName)).Result()
}

// ListFlags returns all flag names sorted alphabetically.
func (f *FeatureFlags) ListFlags(ctx context.Context) ([]string, error) {
	members, err := f.client.SMembers(ctx, f.schema.FlagsIndex()).Result()
	if err != nil {
		return nil, err
	}
	sort.Strings(members)
	return members, nil
}

// ── User targeting ─────────────────────────────────────────────

// AddUser adds a user to the flag allowlist.
func (f *FeatureFlags) AddUser(ctx context.Context, flagName, userID string) error {
	if err := f.assertExists(ctx, flagName); err != nil {
		return err
	}
	return f.client.SAdd(ctx, f.schema.FlagUsers(flagName), userID).Err()
}

// RemoveUser removes a user from the flag allowlist.
func (f *FeatureFlags) RemoveUser(ctx context.Context, flagName, userID string) error {
	return f.client.SRem(ctx, f.schema.FlagUsers(flagName), userID).Err()
}

// ── Cohort targeting ───────────────────────────────────────────

// CreateCohort creates a named cohort.
func (f *FeatureFlags) CreateCohort(ctx context.Context, cohortName string) error {
	return f.cohorts.Create(ctx, cohortName)
}

// DeleteCohort deletes a cohort and cleans up all references.
func (f *FeatureFlags) DeleteCohort(ctx context.Context, cohortName string) error {
	return f.cohorts.Delete(ctx, cohortName)
}

// AddToCohort adds a user to a cohort.
func (f *FeatureFlags) AddToCohort(ctx context.Context, cohortName, userID string) error {
	return f.cohorts.AddUser(ctx, cohortName, userID)
}

// RemoveFromCohort removes a user from a cohort.
func (f *FeatureFlags) RemoveFromCohort(ctx context.Context, cohortName, userID string) error {
	return f.cohorts.RemoveUser(ctx, cohortName, userID)
}

// AddCohortToFlag attaches a cohort to a flag.
func (f *FeatureFlags) AddCohortToFlag(ctx context.Context, flagName, cohortName string) error {
	if err := f.assertExists(ctx, flagName); err != nil {
		return err
	}
	return f.client.SAdd(ctx, f.schema.FlagCohorts(flagName), cohortName).Err()
}

// RemoveCohortFromFlag detaches a cohort from a flag.
func (f *FeatureFlags) RemoveCohortFromFlag(ctx context.Context, flagName, cohortName string) error {
	return f.client.SRem(ctx, f.schema.FlagCohorts(flagName), cohortName).Err()
}

// ListCohorts returns all cohort names sorted alphabetically.
func (f *FeatureFlags) ListCohorts(ctx context.Context) ([]string, error) {
	return f.cohorts.ListCohorts(ctx)
}

// GetCohortMembers returns all members of a cohort.
func (f *FeatureFlags) GetCohortMembers(ctx context.Context, cohortName string) ([]string, error) {
	return f.cohorts.GetMembers(ctx, cohortName)
}

// ── Private helpers ────────────────────────────────────────────

func (f *FeatureFlags) assertExists(ctx context.Context, flagName string) error {
	exists, err := f.client.Exists(ctx, f.schema.Flag(flagName)).Result()
	if err != nil {
		return err
	}
	if exists == 0 {
		return &FlagNotFoundError{FlagName: flagName}
	}
	return nil
}

// SetExpiry sets flag expiry at a unix timestamp.
// 0 means never expires.
func (f *FeatureFlags) SetExpiry(ctx context.Context, flagName string, expiresAt int64, updatedBy string) error {
	if err := f.assertExists(ctx, flagName); err != nil {
		return err
	}
	err := f.client.HSet(ctx, f.schema.Flag(flagName), map[string]string{
		"expires_at": strconv.FormatInt(expiresAt, 10),
		"updated_at": strconv.FormatInt(NowUnix(), 10),
		"updated_by": updatedBy,
	}).Err()
	if err != nil {
		return err
	}
	f.cache.Delete(f.schema.Flag(flagName))
	return nil
}

// SetExpiryIn sets flag expiry as a duration from now.
func (f *FeatureFlags) SetExpiryIn(ctx context.Context, flagName string, d time.Duration, updatedBy string) error {
	expiresAt := time.Now().Add(d).Unix()
	return f.SetExpiry(ctx, flagName, expiresAt, updatedBy)
}

// Env returns the environment name.
func (f *FeatureFlags) Env() string {
	return fmt.Sprintf("%s", f.schema.env)
}