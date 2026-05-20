package featureflags

import (
	"context"
	"sort"

	"github.com/redis/go-redis/v9"
)

// CohortManager handles all cohort operations.
// Uses bidirectional index for O(1) cohort evaluation.
//
// Direction 1: cohort → members   (ff:{env}:cohort:{name})
// Direction 2: user → cohorts     (ff:{env}:user:{id}:cohorts)
type CohortManager struct {
	client *redis.Client
	schema *SchemaKeys
}

// NewCohortManager creates a new CohortManager.
func NewCohortManager(client *redis.Client, schema *SchemaKeys) *CohortManager {
	return &CohortManager{
		client: client,
		schema: schema,
	}
}

// Create registers a cohort in the cohorts index.
func (c *CohortManager) Create(ctx context.Context, cohortName string) error {
	return c.client.SAdd(ctx, c.schema.CohortsIndex(), cohortName).Err()
}

// Delete removes a cohort and cleans both directions of the index.
func (c *CohortManager) Delete(ctx context.Context, cohortName string) error {
	// get all members before deleting
	members, err := c.client.SMembers(ctx, c.schema.Cohort(cohortName)).Result()
	if err != nil {
		return err
	}

	pipe := c.client.Pipeline()

	// clean reverse index for every member
	for _, member := range members {
		pipe.SRem(ctx, c.schema.UserCohorts(member), cohortName)
	}

	// delete cohort Set and remove from index
	pipe.Del(ctx, c.schema.Cohort(cohortName))
	pipe.SRem(ctx, c.schema.CohortsIndex(), cohortName)

	_, err = pipe.Exec(ctx)
	return err
}

// AddUser adds a user to a cohort.
// Writes both directions atomically via pipeline.
func (c *CohortManager) AddUser(ctx context.Context, cohortName, userID string) error {
	pipe := c.client.Pipeline()
	pipe.SAdd(ctx, c.schema.Cohort(cohortName), userID)
	pipe.SAdd(ctx, c.schema.UserCohorts(userID), cohortName)
	_, err := pipe.Exec(ctx)
	return err
}

// RemoveUser removes a user from a cohort.
// Removes both directions atomically via pipeline.
func (c *CohortManager) RemoveUser(ctx context.Context, cohortName, userID string) error {
	pipe := c.client.Pipeline()
	pipe.SRem(ctx, c.schema.Cohort(cohortName), userID)
	pipe.SRem(ctx, c.schema.UserCohorts(userID), cohortName)
	_, err := pipe.Exec(ctx)
	return err
}

// GetMembers returns all members of a cohort.
func (c *CohortManager) GetMembers(ctx context.Context, cohortName string) ([]string, error) {
	return c.client.SMembers(ctx, c.schema.Cohort(cohortName)).Result()
}

// ListCohorts returns all cohort names sorted alphabetically.
func (c *CohortManager) ListCohorts(ctx context.Context) ([]string, error) {
	members, err := c.client.SMembers(ctx, c.schema.CohortsIndex()).Result()
	if err != nil {
		return nil, err
	}
	sort.Strings(members)
	return members, nil
}

// Exists checks if a cohort exists in the index.
func (c *CohortManager) Exists(ctx context.Context, cohortName string) (bool, error) {
	return c.client.SIsMember(ctx, c.schema.CohortsIndex(), cohortName).Result()
}