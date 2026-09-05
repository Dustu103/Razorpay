package models

import "time"

// Payment Rail constants
const (
	PaymentRailNACH = "nach"
	PaymentRailUPI  = "upi"
	PaymentRailCard = "card"
)

// Product Type constants
const (
	ProductTypeSIP              = "sip"
	ProductTypeLoanEMI          = "loan_emi"
	ProductTypeInsurancePremium = "insurance_premium"
)

// Consequence Severity constants
const (
	ConsequenceCreditScoreRisk     = "credit_score_risk"
	ConsequenceInvestmentLapseRisk = "investment_lapse_risk"
	ConsequencePolicyLapseRisk     = "policy_lapse_risk"
)

// Recommended Action constants
const (
	ActionSIPCancellationRiskEscalate = "sip_cancellation_risk_escalate"
	ActionCreditScoreRiskEscalate     = "credit_score_risk_escalate"
	ActionPolicyLapseRiskEscalate     = "policy_lapse_risk_escalate"
	ActionNACHDoNotRetry              = "nach_do_not_retry"
	ActionRetryScheduled              = "retry_scheduled"
	ActionTriggerDunningWhatsApp      = "trigger_dunning_whatsapp"
	ActionTriggerDunningSMS           = "trigger_dunning_sms"
	ActionTriggerDunningEmail         = "trigger_dunning_email"
)

// Failure Causes
const (
	CauseInsufficientFunds       = "insufficient_funds"
	CauseBankTechnicalError      = "bank_technical_error"
	CauseMandateExpired          = "mandate_expired"
	CauseAccountFrozenOrClosed   = "account_frozen_or_closed"
	CauseIncorrectMandateDetails = "incorrect_mandate_details"
)

// MandateTransaction represents a failed recurring debit
type MandateTransaction struct {
	ID                      string     `json:"id"`
	PaymentRail             string     `json:"payment_rail"`
	ProductType             string     `json:"product_type"`
	MandateValue            float64    `json:"mandate_value"`
	Cause                   string     `json:"cause"`
	ConsecutiveFailureCount int        `json:"consecutive_failure_count"`
	DaysSinceDueDate        *int       `json:"days_since_due_date,omitempty"`
	CreatedAt               time.Time  `json:"created_at"`
}

// EvaluationRequest is sent to evaluate a transaction via REST API
type EvaluationRequest struct {
	TransactionID           string  `json:"transaction_id"`
	PaymentRail             string  `json:"payment_rail"`
	ProductType             string  `json:"product_type"`
	MandateValue            float64 `json:"mandate_value"`
	Cause                   string  `json:"cause"`
	ConsecutiveFailureCount int     `json:"consecutive_failure_count"`
	DaysSinceDueDate        *int    `json:"days_since_due_date,omitempty"`
}

// EvaluationResponse is the decision from the Governor & Urgency Router
type EvaluationResponse struct {
	TransactionID       string  `json:"transaction_id"`
	Action              string  `json:"action"`
	GovernorStopped     bool    `json:"governor_stopped"`
	UrgencyTier         string  `json:"urgency_tier"`         // "critical" | "elevated" | "standard"
	RecommendedChannel  string  `json:"recommended_channel"`  // "whatsapp" | "sms" | "email"
	ConsequenceSeverity string  `json:"consequence_severity"` // "credit_score_risk" | "investment_lapse_risk" | "policy_lapse_risk" | ""
	Confidence          float64 `json:"confidence"`
	Reasoning           string  `json:"reasoning"`
	RecoveryProbability float64 `json:"recovery_probability"`
}

// NACHMetricsResponse holds aggregated metrics for the dashboard
type NACHMetricsResponse struct {
	TotalMandatesEvaluated int64              `json:"total_mandates_evaluated"`
	GovernorPreEmptions    int64              `json:"governor_pre_emptions"`
	UnretryableHardStops   int64              `json:"unretryable_hard_stops"`
	BankRetryFeesSavedINR  float64            `json:"bank_retry_fees_saved_inr"`
	RevenueRecoveredINR    float64            `json:"revenue_recovered_inr"`
	RecentEvaluations      []EvaluationResponse `json:"recent_evaluations"`
}
