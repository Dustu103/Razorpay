package models

import "time"

// Transaction is fetched from DB by the classification worker.
type Transaction struct {
	ID                         string
	GatewayTransactionID       string
	StatusCode                 string
	NPCIResponseCode           *string
	BankResponseCode           *string
	Amount                     float64
	CustomerBank               *string
	RetryCountSoFar            int
	MandateNotificationSentAt  *time.Time
	DebitScheduledAt           *time.Time
}

// ClassificationJob is read from the Redis queue.
type ClassificationJob struct {
	TransactionID string `json:"transaction_id"`
}

// ClassificationResult is what gets written to the classifications table.
type ClassificationResult struct {
	TransactionID     string
	Layer             int
	Cause             string
	Confidence        float64
	Reasoning         string
	RecommendedAction string
	ModelVersion      *string // nil for Layer 1
}

// Cause constants match the TDD taxonomy.
const (
	CauseNotificationComplianceBlock = "notification_compliance_block"
	CauseSoftDecline                 = "soft_decline"
	CauseHardDecline                 = "hard_decline"
	CauseGatewayFault                = "gateway_fault"
	CauseFraudFilterBlock            = "fraud_filter_block"
)

// RecommendedAction constants.
const (
	ActionSilentReschedule = "silent_reschedule"
	ActionRetryNow         = "retry_now"
	ActionRetryScheduled   = "retry_scheduled"
	ActionDoNotRetry       = "do_not_retry"
	ActionReverifyReverse  = "reverify_and_reverse"
)

// Confidence Thresholds for Layer 2 predictions.
const (
	ThresholdReverifyReverse = 0.85
	ThresholdRetry           = 0.55
	ThresholdDoNotRetry      = 0.55
)
