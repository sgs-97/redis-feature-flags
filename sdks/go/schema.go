package featureflags

import "fmt"

// SchemaKeys builds Redis key names for all flag and cohort operations.
// All keys are namespaced by environment — ff:{env}:...
// This ensures prod, staging, and dev are fully isolated on one Redis instance.
type SchemaKeys struct {
	env string
}

// NewSchemaKeys creates a new SchemaKeys for the given environment.
func NewSchemaKeys(env string) *SchemaKeys {
	return &SchemaKeys{env: env}
}

// Flag returns the key for the flag Hash.
// ff:{env}:flag:{name}
func (s *SchemaKeys) Flag(flagName string) string {
	return fmt.Sprintf("ff:%s:flag:%s", s.env, flagName)
}

// FlagUsers returns the key for the flag user allowlist Set.
// ff:{env}:flag:{name}:users
func (s *SchemaKeys) FlagUsers(flagName string) string {
	return fmt.Sprintf("ff:%s:flag:%s:users", s.env, flagName)
}

// FlagCohorts returns the key for the flag cohort allowlist Set.
// ff:{env}:flag:{name}:cohorts
func (s *SchemaKeys) FlagCohorts(flagName string) string {
	return fmt.Sprintf("ff:%s:flag:%s:cohorts", s.env, flagName)
}

// FlagHistory returns the key for the flag history List.
// ff:{env}:flag:{name}:history
func (s *SchemaKeys) FlagHistory(flagName string) string {
	return fmt.Sprintf("ff:%s:flag:%s:history", s.env, flagName)
}

// Cohort returns the key for the cohort members Set.
// ff:{env}:cohort:{name}
func (s *SchemaKeys) Cohort(cohortName string) string {
	return fmt.Sprintf("ff:%s:cohort:%s", s.env, cohortName)
}

// UserCohorts returns the key for the user reverse index Set.
// ff:{env}:user:{id}:cohorts
func (s *SchemaKeys) UserCohorts(userID string) string {
	return fmt.Sprintf("ff:%s:user:%s:cohorts", s.env, userID)
}

// FlagsIndex returns the key for the flags index Set.
// ff:{env}:flags:__index__
func (s *SchemaKeys) FlagsIndex() string {
	return fmt.Sprintf("ff:%s:flags:__index__", s.env)
}

// CohortsIndex returns the key for the cohorts index Set.
// ff:{env}:cohorts:__index__
func (s *SchemaKeys) CohortsIndex() string {
	return fmt.Sprintf("ff:%s:cohorts:__index__", s.env)
}

// SchemaVersion returns the key for the schema version String.
// ff:{env}:__schema__
func (s *SchemaKeys) SchemaVersion() string {
	return fmt.Sprintf("ff:%s:__schema__", s.env)
}