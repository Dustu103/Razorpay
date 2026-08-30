package worker

import (
	"context"
	"encoding/json"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
	"razorpay-classification-service/internal/layer2"
)

// BNPLDefaultEvent represents an incoming missed BNPL installment.
type BNPLDefaultEvent struct {
	BorrowerID              string  `json:"borrower_id"`
	InternalDebt            float64 `json:"internal_debt"`
	ExternalDebt            float64 `json:"external_ecosystem_debt"` // "Phantom Debt"
	DaysSinceLogin          int     `json:"days_since_login"`
	DemographicAge          int     `json:"demographic_age"`
	
	// Preprocessing gate fields for DPDP compliance.
	// NOTE: In production, these should be hydrated from PostgreSQL via a transaction
	// that guarantees consistency with the Account Aggregator webhook updates.
	ConsentRevoked          bool    `json:"consent_revoked"`
	ExternalDebtDataAgeDays int     `json:"external_debt_data_age_days"`
}

// StartBNPLWorker listens to a Redis queue for BNPL defaults and processes them.
func StartBNPLWorker(rdb *redis.Client, queueName string) {
	ctx := context.Background()
	log.Printf("Starting BNPL Worker on queue: %s", queueName)

	for {
		// BLPop blocks until a job is available
		result, err := rdb.BLPop(ctx, 0, queueName).Result()
		if err != nil {
			log.Printf("Error popping from BNPL queue: %v", err)
			time.Sleep(1 * time.Second)
			continue
		}

		payload := result[1]
		var event BNPLDefaultEvent
		if err := json.Unmarshal([]byte(payload), &event); err != nil {
			log.Printf("Error unmarshalling BNPL event: %v", err)
			continue
		}

		log.Printf("Processing BNPL Default for Borrower: %s", event.BorrowerID)
		processBNPLDefault(event)
	}
}

func processBNPLDefault(event BNPLDefaultEvent) {
	// Step 1: Query the Heavy ML Model for the best recovery channel
	channel, err := layer2.EvaluateBNPLRecovery(
		event.BorrowerID,
		event.InternalDebt,
		event.ExternalDebt,
		event.DaysSinceLogin,
		event.DemographicAge,
		event.ConsentRevoked,
		event.ExternalDebtDataAgeDays,
	)

	if err != nil {
		log.Printf("[BNPL] ML Inference failed for %s: %v", event.BorrowerID, err)
		return
	}
	
	log.Printf("[BNPL] ML Recommends Channel '%s' for Borrower %s", channel, event.BorrowerID)

	// Step 2: STRICT RBI COMPLIANCE CIRCUIT BREAKER
	// Regardless of whether it's SMS, Email, or Voice, we MUST check compliance.
	allowed, reason, err := layer2.CheckRBICompliance(event.BorrowerID)
	
	if err != nil {
		// FAIL CLOSED: If we can't verify compliance, we DO NOT send the message.
		log.Printf("[BNPL CIRCUIT BREAKER] Compliance check failed for %s: %v. Dropping action.", event.BorrowerID, err)
		return
	}

	if !allowed {
		log.Printf("[BNPL CIRCUIT BREAKER] ACTION BLOCKED for %s. Reason: %s", event.BorrowerID, reason)
		// Here we would typically push this back to a delayed queue for tomorrow morning.
		return
	}

	// Step 3: Dispatch the action and write to Audit Trail
	log.Printf("[BNPL] SUCCESS: Dispatching %s recovery message to Borrower %s (Compliance passed)", channel, event.BorrowerID)
	
	// Write the action to PostgreSQL for the audit trail
	// TODO: Replace with actual DB transaction in production
	// e.g., db.Exec("INSERT INTO bnpl_recovery_actions (borrower_id, channel, dispatched_at) VALUES ($1, $2, NOW())", event.BorrowerID, channel)
	log.Printf("[DB WRITE] INSERT INTO bnpl_recovery_actions: Borrower=%s | Channel=%s", event.BorrowerID, channel)
}
