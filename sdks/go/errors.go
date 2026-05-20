package featureflags

import "fmt"

// RedisFlagError is the base error type for all library errors.
type RedisFlagError struct {
	Message string
}

func (e *RedisFlagError) Error() string {
	return e.Message
}

// FlagNotFoundError is returned when a flag does not exist.
type FlagNotFoundError struct {
	FlagName string
}

func (e *FlagNotFoundError) Error() string {
	return fmt.Sprintf(
		"Flag '%s' not found. Create it with: flags.Create(ctx, \"%s\", 0)",
		e.FlagName, e.FlagName,
	)
}

// CohortNotFoundError is returned when a cohort does not exist.
type CohortNotFoundError struct {
	CohortName string
}

func (e *CohortNotFoundError) Error() string {
	return fmt.Sprintf(
		"Cohort '%s' not found. Create it with: flags.CreateCohort(ctx, \"%s\")",
		e.CohortName, e.CohortName,
	)
}

// InvalidRolloutError is returned when rollout is not between 0 and 100.
type InvalidRolloutError struct {
	Value int
}

func (e *InvalidRolloutError) Error() string {
	return fmt.Sprintf(
		"Rollout must be between 0 and 100. Got: %d",
		e.Value,
	)
}

// RedisConnectionError is returned when Redis is unreachable
// and no stale cache is available.
type RedisConnectionError struct {
	Message string
}

func (e *RedisConnectionError) Error() string {
	return fmt.Sprintf("Redis connection error: %s", e.Message)
}

// SchemaVersionError is returned when Redis schema is newer than SDK supports.
type SchemaVersionError struct {
	Expected string
	Found    string
}

func (e *SchemaVersionError) Error() string {
	return fmt.Sprintf(
		"Schema version mismatch. SDK supports %s, Redis has %s. Please upgrade redis-feature-flags.",
		e.Expected, e.Found,
	)
}