package governor

import (
	"fmt"

	"razorpay-nach-recovery-service/internal/models"
)

// Governor thresholds
const (
	SIPEscalateAtFailures       = 2 // Pre-emptive escalation before AMC threshold (3)
	SIPHardStopAtFailures       = 3 // AMC auto-cancellation threshold
	EMICreditRiskAtDays         = 28 // 2 days before 30-day bureau reporting
	InsuranceEscalateAtFailures = 1  // Immediate policy lapse risk
)

// Unretryable permanent failure causes
var permanentCauses = map[string]bool{
	models.CauseMandateExpired:          true,
	models.CauseAccountFrozenOrClosed:   true,
	models.CauseIncorrectMandateDetails: true,
}

// Evaluate evaluates a mandate transaction against the Governor rules and urgency policies.
func Evaluate(req *models.EvaluationRequest) models.EvaluationResponse {
	// If not NACH, pass-through
	if req.PaymentRail != "" && req.PaymentRail != models.PaymentRailNACH {
		return models.EvaluationResponse{
			TransactionID:       req.TransactionID,
			Action:              models.ActionRetryScheduled,
			GovernorStopped:     false,
			UrgencyTier:         "standard",
			RecommendedChannel:  "email",
			ConsequenceSeverity: "",
			Confidence:          0.50,
			Reasoning:           "Non-NACH transaction: Governor pass-through.",
			RecoveryProbability: 0.50,
		}
	}

	// 1. Check Governor Layer 0 Short-Circuits (Product Deadlines)
	switch req.ProductType {
	case models.ProductTypeSIP:
		if req.ConsecutiveFailureCount >= SIPHardStopAtFailures {
			return models.EvaluationResponse{
				TransactionID:       req.TransactionID,
				Action:              models.ActionSIPCancellationRiskEscalate,
				GovernorStopped:     true,
				UrgencyTier:         "elevated",
				RecommendedChannel:  "sms",
				ConsequenceSeverity: models.ConsequenceInvestmentLapseRisk,
				Confidence:          1.0,
				Reasoning: fmt.Sprintf(
					"[Governor · SIP Hard Stop] %d consecutive failures reached the AMC cancellation threshold (%d). "+
						"Mandate retry BLOCKED — automated retry is non-compliant. Escalated to SMS dunning.",
					req.ConsecutiveFailureCount, SIPHardStopAtFailures,
				),
				RecoveryProbability: 0.45,
			}
		}
		if req.ConsecutiveFailureCount >= SIPEscalateAtFailures {
			return models.EvaluationResponse{
				TransactionID:       req.TransactionID,
				Action:              models.ActionSIPCancellationRiskEscalate,
				GovernorStopped:     true,
				UrgencyTier:         "elevated",
				RecommendedChannel:  "sms",
				ConsequenceSeverity: models.ConsequenceInvestmentLapseRisk,
				Confidence:          0.95,
				Reasoning: fmt.Sprintf(
					"[Governor · SIP Pre-Emptive] %d failures detected. AMC threshold is %d. "+
						"Escalating before auto-cancellation to protect investor portfolio.",
					req.ConsecutiveFailureCount, SIPHardStopAtFailures,
				),
				RecoveryProbability: 0.65,
			}
		}

	case models.ProductTypeLoanEMI:
		if req.DaysSinceDueDate != nil && *req.DaysSinceDueDate >= EMICreditRiskAtDays {
			return models.EvaluationResponse{
				TransactionID:       req.TransactionID,
				Action:              models.ActionCreditScoreRiskEscalate,
				GovernorStopped:     true,
				UrgencyTier:         "critical",
				RecommendedChannel:  "whatsapp",
				ConsequenceSeverity: models.ConsequenceCreditScoreRisk,
				Confidence:          1.0,
				Reasoning: fmt.Sprintf(
					"[Governor · EMI Credit Risk] %d days past due date. Credit bureau reporting begins at 30 days. "+
						"Immediate WhatsApp intervention forced to protect borrower credit score.",
					*req.DaysSinceDueDate,
				),
				RecoveryProbability: 0.72,
			}
		}

	case models.ProductTypeInsurancePremium:
		if req.ConsecutiveFailureCount >= InsuranceEscalateAtFailures {
			return models.EvaluationResponse{
				TransactionID:       req.TransactionID,
				Action:              models.ActionPolicyLapseRiskEscalate,
				GovernorStopped:     true,
				UrgencyTier:         "elevated",
				RecommendedChannel:  "sms",
				ConsequenceSeverity: models.ConsequencePolicyLapseRisk,
				Confidence:          0.90,
				Reasoning: fmt.Sprintf(
					"[Governor · Insurance Lapse] %d failure detected on premium mandate. "+
						"Policy coverage lapse risk is immediate. High-urgency SMS dispatched.",
					req.ConsecutiveFailureCount,
				),
				RecoveryProbability: 0.60,
			}
		}
	}

	// 2. Check Permanent Unretryable Bank Causes
	if permanentCauses[req.Cause] {
		consequence := resolveConsequence(req.ProductType)
		channel := "sms"
		tier := "elevated"
		if consequence == models.ConsequenceCreditScoreRisk {
			channel = "whatsapp"
			tier = "critical"
		}

		return models.EvaluationResponse{
			TransactionID:       req.TransactionID,
			Action:              models.ActionNACHDoNotRetry,
			GovernorStopped:     true,
			UrgencyTier:         tier,
			RecommendedChannel:  channel,
			ConsequenceSeverity: consequence,
			Confidence:          1.0,
			Reasoning: fmt.Sprintf(
				"[Governor · Permanent Cause] Failure cause %q cannot be retried. "+
				"Eliminating bank retry penalty (₹250-₹500 saved). Directing customer to update mandate.",
				req.Cause,
			),
			RecoveryProbability: 0.0,
		}
	}

	// 3. Soft Retryable Causes (insufficient_funds, bank_technical_error)
	consequence := resolveConsequence(req.ProductType)
	channel := "email"
	tier := "standard"

	if consequence == models.ConsequenceCreditScoreRisk {
		channel = "whatsapp"
		tier = "critical"
	} else if consequence != "" {
		channel = "sms"
		tier = "elevated"
	}

	return models.EvaluationResponse{
		TransactionID:       req.TransactionID,
		Action:              models.ActionRetryScheduled,
		GovernorStopped:     false,
		UrgencyTier:         tier,
		RecommendedChannel:  channel,
		ConsequenceSeverity: consequence,
		Confidence:          0.85,
		Reasoning: fmt.Sprintf(
			"[Governor · Retry Viable] Cause %q is soft and retryable. Retry scheduled; fallback channel is %s.",
			req.Cause, channel,
		),
		RecoveryProbability: 0.70,
	}
}

func resolveConsequence(productType string) string {
	switch productType {
	case models.ProductTypeLoanEMI:
		return models.ConsequenceCreditScoreRisk
	case models.ProductTypeSIP:
		return models.ConsequenceInvestmentLapseRisk
	case models.ProductTypeInsurancePremium:
		return models.ConsequencePolicyLapseRisk
	default:
		return ""
	}
}
