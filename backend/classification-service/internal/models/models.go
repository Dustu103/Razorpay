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

	// NACH rail fields — zero-valued for UPI/card transactions.
	PaymentRail             string // "nach" | "upi" | "card" | ""
	ProductType             string // "sip" | "loan_emi" | "insurance_premium" | ""
	ConsecutiveFailureCount int    // Number of consecutive mandate debit failures
	DaysSinceDueDate        *int   // EMI: days elapsed since scheduled due date
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
	// Shared causes (UPI, card, NACH)
	CauseNotificationComplianceBlock = "notification_compliance_block"
	CauseSoftDecline                 = "soft_decline"
	CauseHardDecline                 = "hard_decline"
	CauseGatewayFault                = "gateway_fault"
	CauseFraudFilterBlock            = "fraud_filter_block"

	// NACH-specific causes — surfaced by Layer 3 when payment_rail == "nach".
	CauseNACHInsufficientFunds       = "nach_insufficient_funds"
	CauseNACHMandateExpired          = "nach_mandate_expired"
	CauseNACHAccountFrozenOrClosed   = "nach_account_frozen_or_closed"
	CauseNACHBankTechnicalError      = "nach_bank_technical_error"
	CauseNACHIncorrectMandateDetails = "nach_incorrect_mandate_details"
)

// RecommendedAction constants.
const (
	// Shared actions
	ActionSilentReschedule = "silent_reschedule"
	ActionRetryNow         = "retry_now"
	ActionRetryScheduled   = "retry_scheduled"
	ActionDoNotRetry       = "do_not_retry"
	ActionReverifyReverse  = "reverify_and_reverse"

	// NACH-specific escalation actions (product-aware).
	ActionSIPCancellationRiskEscalate = "sip_cancellation_risk_escalate"
	ActionCreditScoreRiskEscalate     = "credit_score_risk_escalate"
	ActionPolicyLapseRiskEscalate     = "policy_lapse_risk_escalate"
	ActionNACHDoNotRetry              = "nach_do_not_retry"
)

// Payment rail constants.
const (
	PaymentRailNACH = "nach"
	PaymentRailUPI  = "upi"
	PaymentRailCard = "card"
)

// Product type constants (NACH mandates only).
const (
	ProductTypeSIP              = "sip"
	ProductTypeLoanEMI          = "loan_emi"
	ProductTypeInsurancePremium = "insurance_premium"
)

// Consequence severity constants — used in dunning routing and audit trail.
const (
	ConsequenceCreditScoreRisk     = "credit_score_risk"
	ConsequenceInvestmentLapseRisk = "investment_lapse_risk"
	ConsequencePolicyLapseRisk     = "policy_lapse_risk"
)

// Confidence Thresholds for Layer 2 predictions.
const (
	// Fine-tuned thresholds based on Random Forest confidence calibration
	ThresholdReverifyReverse = 0.85 // Strict for extreme risk actions
	ThresholdRetry           = 0.65 // Optimized for standard retries
	ThresholdDoNotRetry      = 0.70 // Optimized for blocking actions
)
