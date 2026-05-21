package featureflags

import (
	"context"
	"testing"

	"github.com/redis/go-redis/v9"
)

// helper — creates real Redis client on port 6379
func newTestClient(t *testing.T) *redis.Client {
	client := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})
	ctx := context.Background()
	if err := client.Ping(ctx).Err(); err != nil {
		t.Skip("Redis not available — skipping tests")
	}
	return client
}

// helper — creates FeatureFlags and flushes test namespace after test
func newTestFlags(t *testing.T) (*FeatureFlags, func()) {
	client := newTestClient(t)
	flags := New(client, "gotest")
	ctx := context.Background()

	cleanup := func() {
		keys, _ := client.Keys(ctx, "ff:gotest:*").Result()
		if len(keys) > 0 {
			client.Del(ctx, keys...)
		}
		client.Close()
	}

	return flags, cleanup
}

// ── Schema tests ───────────────────────────────────────────────

func TestSchemaKeys(t *testing.T) {
	s := NewSchemaKeys("prod")

	if got := s.Flag("dark_mode"); got != "ff:prod:flag:dark_mode" {
		t.Errorf("Flag() = %s, want ff:prod:flag:dark_mode", got)
	}
	if got := s.FlagUsers("dark_mode"); got != "ff:prod:flag:dark_mode:users" {
		t.Errorf("FlagUsers() = %s, want ff:prod:flag:dark_mode:users", got)
	}
	if got := s.FlagCohorts("dark_mode"); got != "ff:prod:flag:dark_mode:cohorts" {
		t.Errorf("FlagCohorts() = %s, want ff:prod:flag:dark_mode:cohorts", got)
	}
	if got := s.Cohort("beta"); got != "ff:prod:cohort:beta" {
		t.Errorf("Cohort() = %s, want ff:prod:cohort:beta", got)
	}
	if got := s.UserCohorts("alice"); got != "ff:prod:user:alice:cohorts" {
		t.Errorf("UserCohorts() = %s, want ff:prod:user:alice:cohorts", got)
	}
	if got := s.FlagsIndex(); got != "ff:prod:flags:__index__" {
		t.Errorf("FlagsIndex() = %s, want ff:prod:flags:__index__", got)
	}
}

// ── Utils tests ────────────────────────────────────────────────

func TestEvaluateRolloutZero(t *testing.T) {
	/*
	 * Given: rollout=0
	 * Expected: false — nobody in 0% rollout
	 */
	if EvaluateRollout("dark_mode", "alice", 0) {
		t.Error("rollout=0 should return false")
	}
}

func TestEvaluateRolloutHundred(t *testing.T) {
	/*
	 * Given: rollout=100
	 * Expected: true — everyone in 100% rollout
	 */
	if !EvaluateRollout("dark_mode", "alice", 100) {
		t.Error("rollout=100 should return true")
	}
}

func TestEvaluateRolloutDeterministic(t *testing.T) {
	/*
	 * Given: same flag, same user, same rollout — called 1000 times
	 * Expected: all results identical — SHA-256 is deterministic
	 */
	first := EvaluateRollout("dark_mode", "alice", 50)
	for i := 0; i < 1000; i++ {
		if EvaluateRollout("dark_mode", "alice", 50) != first {
			t.Error("rollout should be deterministic")
		}
	}
}

func TestIsExpiredZero(t *testing.T) {
	/*
	 * Given: expires_at=0
	 * Expected: false — 0 means never expires
	 */
	if IsExpired(0) {
		t.Error("expires_at=0 should never expire")
	}
}

func TestIsExpiredPast(t *testing.T) {
	/*
	 * Given: expires_at=1000 (year 1970 — definitely past)
	 * Expected: true — flag has expired
	 */
	if !IsExpired(1000) {
		t.Error("past timestamp should be expired")
	}
}

func TestIsExpiredFuture(t *testing.T) {
	/*
	 * Given: expires_at = now + 86400
	 * Expected: false — flag has not expired yet
	 */
	if IsExpired(NowUnix() + 86400) {
		t.Error("future timestamp should not be expired")
	}
}

// ── Cache tests ────────────────────────────────────────────────

func TestCacheGetSetDelete(t *testing.T) {
	/*
	 * Given: data stored in cache
	 * Expected: get returns same data, delete removes it
	 */
	cache := NewLocalCache(30)
	data := map[string]string{"enabled": "1", "rollout": "10"}

	cache.Set("key1", data)

	got := cache.Get("key1")
	if got == nil {
		t.Fatal("expected data but got nil")
	}
	if got["enabled"] != "1" {
		t.Errorf("enabled = %s, want 1", got["enabled"])
	}

	cache.Delete("key1")
	if cache.Get("key1") != nil {
		t.Error("expected nil after delete")
	}
}

func TestCacheGetStaleAfterExpiry(t *testing.T) {
	/*
	 * Given: cache with TTL=0 (expires immediately)
	 * Expected: get returns nil, getStale returns data
	 */
	cache := NewLocalCache(0)
	data := map[string]string{"enabled": "1"}
	cache.Set("key1", data)

	if cache.Get("key1") != nil {
		t.Error("expected nil for expired entry")
	}
	if cache.GetStale("key1") == nil {
		t.Error("expected stale data")
	}
}

func TestCacheMissReturnsNil(t *testing.T) {
	/*
	 * Given: empty cache
	 * Expected: get returns nil
	 */
	cache := NewLocalCache(30)
	if cache.Get("nonexistent") != nil {
		t.Error("expected nil for missing key")
	}
}

// ── Flag lifecycle tests ───────────────────────────────────────

func TestCreateFlagDisabledByDefault(t *testing.T) {
	/*
	 * Given: flag created with no arguments
	 * Expected: IsEnabled returns false — disabled by default
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	if err := flags.Create(ctx, "dark_mode", 0, "test"); err != nil {
		t.Fatalf("Create failed: %v", err)
	}

	enabled, err := flags.IsEnabled(ctx, "dark_mode", "alice")
	if err != nil {
		t.Fatalf("IsEnabled failed: %v", err)
	}
	if enabled {
		t.Error("new flag should be disabled by default")
	}
}

func TestEnableFlag(t *testing.T) {
	/*
	 * Given: flag created and enabled with rollout=100
	 * Expected: IsEnabled returns true
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	flags.Create(ctx, "dark_mode", 100, "test")
	flags.Enable(ctx, "dark_mode", "test")

	enabled, _ := flags.IsEnabled(ctx, "dark_mode", "alice")
	if !enabled {
		t.Error("enabled flag with rollout=100 should return true")
	}
}

func TestDisableFlag(t *testing.T) {
	/*
	 * Given: flag enabled then disabled
	 * Expected: IsEnabled returns false — kill switch works
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	flags.Create(ctx, "dark_mode", 100, "test")
	flags.Enable(ctx, "dark_mode", "test")
	flags.Disable(ctx, "dark_mode", "test")

	enabled, _ := flags.IsEnabled(ctx, "dark_mode", "alice")
	if enabled {
		t.Error("disabled flag should return false")
	}
}

func TestEnableNonexistentFlagReturnsError(t *testing.T) {
	/*
	 * Given: flag does not exist
	 * Expected: Enable returns FlagNotFoundError
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	err := flags.Enable(ctx, "nonexistent", "test")
	if err == nil {
		t.Error("expected error for nonexistent flag")
	}
}

func TestInvalidRolloutReturnsError(t *testing.T) {
	/*
	 * Given: rollout=150
	 * Expected: Create returns InvalidRolloutError
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	err := flags.Create(ctx, "dark_mode", 150, "test")
	if err == nil {
		t.Error("expected error for invalid rollout")
	}
}

func TestDeleteFlag(t *testing.T) {
	/*
	 * Given: flag created then deleted
	 * Expected: IsEnabled returns false — flag gone
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	flags.Create(ctx, "dark_mode", 100, "test")
	flags.Enable(ctx, "dark_mode", "test")
	flags.Delete(ctx, "dark_mode")

	enabled, _ := flags.IsEnabled(ctx, "dark_mode", "alice")
	if enabled {
		t.Error("deleted flag should return false")
	}
}

func TestListFlags(t *testing.T) {
	/*
	 * Given: three flags created
	 * Expected: ListFlags returns all three sorted
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	flags.Create(ctx, "zebra_flag", 0, "test")
	flags.Create(ctx, "alpha_flag", 0, "test")
	flags.Create(ctx, "middle_flag", 0, "test")

	list, err := flags.ListFlags(ctx)
	if err != nil {
		t.Fatalf("ListFlags failed: %v", err)
	}
	if len(list) != 3 {
		t.Errorf("expected 3 flags, got %d", len(list))
	}
	if list[0] != "alpha_flag" {
		t.Errorf("expected alpha_flag first, got %s", list[0])
	}
}

// ── User targeting tests ───────────────────────────────────────

func TestAddUserToAllowlist(t *testing.T) {
	/*
	 * Given: flag with rollout=0. Alice added to allowlist.
	 * Expected: IsEnabled returns true for alice, false for bob.
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	flags.Create(ctx, "dark_mode", 0, "test")
	flags.Enable(ctx, "dark_mode", "test")
	flags.AddUser(ctx, "dark_mode", "alice")

	enabled, _ := flags.IsEnabled(ctx, "dark_mode", "alice")
	if !enabled {
		t.Error("alice in allowlist should get flag")
	}

	enabled, _ = flags.IsEnabled(ctx, "dark_mode", "bob")
	if enabled {
		t.Error("bob not in allowlist should not get flag")
	}
}

func TestRemoveUserFromAllowlist(t *testing.T) {
	/*
	 * Given: alice added then removed from allowlist
	 * Expected: IsEnabled returns false for alice
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	flags.Create(ctx, "dark_mode", 0, "test")
	flags.Enable(ctx, "dark_mode", "test")
	flags.AddUser(ctx, "dark_mode", "alice")
	flags.RemoveUser(ctx, "dark_mode", "alice")

	enabled, _ := flags.IsEnabled(ctx, "dark_mode", "alice")
	if enabled {
		t.Error("removed user should not get flag")
	}
}

// ── Cohort targeting tests ─────────────────────────────────────

func TestCohortTargeting(t *testing.T) {
	/*
	 * Given: alice in beta-testers. beta-testers attached to flag.
	 * Expected: true for alice, false for charlie.
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	flags.Create(ctx, "dark_mode", 0, "test")
	flags.Enable(ctx, "dark_mode", "test")
	flags.CreateCohort(ctx, "beta-testers")
	flags.AddToCohort(ctx, "beta-testers", "alice")
	flags.AddCohortToFlag(ctx, "dark_mode", "beta-testers")

	enabled, _ := flags.IsEnabled(ctx, "dark_mode", "alice")
	if !enabled {
		t.Error("alice in cohort should get flag")
	}

	enabled, _ = flags.IsEnabled(ctx, "dark_mode", "charlie")
	if enabled {
		t.Error("charlie not in cohort should not get flag")
	}
}

func TestRemoveCohortFromFlag(t *testing.T) {
	/*
	 * Given: beta-testers attached then removed from flag.
	 * Expected: alice no longer gets flag via cohort.
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	flags.Create(ctx, "dark_mode", 0, "test")
	flags.Enable(ctx, "dark_mode", "test")
	flags.CreateCohort(ctx, "beta-testers")
	flags.AddToCohort(ctx, "beta-testers", "alice")
	flags.AddCohortToFlag(ctx, "dark_mode", "beta-testers")
	flags.RemoveCohortFromFlag(ctx, "dark_mode", "beta-testers")

	enabled, _ := flags.IsEnabled(ctx, "dark_mode", "alice")
	if enabled {
		t.Error("alice should not get flag after cohort removed")
	}
}

// ── Missing flag tests ─────────────────────────────────────────

func TestMissingFlagReturnsDefault(t *testing.T) {
	/*
	 * Given: flag does not exist
	 * Expected: IsEnabled returns false — default
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	enabled, _ := flags.IsEnabled(ctx, "nonexistent", "alice")
	if enabled {
		t.Error("missing flag should return false")
	}
}

func TestMissingFlagReturnsCustomDefault(t *testing.T) {
	/*
	 * Given: flag does not exist, custom default=true
	 * Expected: IsEnabled returns true
	 */
	ctx := context.Background()
	flags, cleanup := newTestFlags(t)
	defer cleanup()

	enabled, _ := flags.IsEnabledWithDefault(ctx, "nonexistent", "alice", true)
	if !enabled {
		t.Error("missing flag should return custom default true")
	}
}