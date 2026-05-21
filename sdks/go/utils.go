package featureflags

import (
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"time"
)

// EvaluateRollout determines if a user is in the rollout bucket.
// Uses SHA-256 hashing of "flagName:userID" modulo 100.
// Same flag + user always returns same result — deterministic, no randomness.
func EvaluateRollout(flagName, userID string, rollout int) bool {
	if rollout <= 0 {
		return false
	}
	if rollout >= 100 {
		return true
	}

	key := fmt.Sprintf("%s:%s", flagName, userID)
	hash := sha256.Sum256([]byte(key))

	// take first 4 bytes as unsigned int
	value := binary.BigEndian.Uint32(hash[:4])
	bucket := int(value % 100)

	return bucket < rollout
}

// NowUnix returns the current unix timestamp in seconds — UTC.
func NowUnix() int64 {
	return time.Now().Unix()
}

// IsExpired checks if a unix timestamp has passed.
// 0 means never expires.
func IsExpired(expiresAt int64) bool {
	if expiresAt == 0 {
		return false
	}
	return NowUnix() > expiresAt
}