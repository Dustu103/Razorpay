// Package nach implements the NACH mandate stopping policy.
//
// This is Layer 0 of the classification pipeline — it runs before Layer 1
// (RBI notification compliance) and before any ML/LLM inference. It answers
// two questions for every NACH transaction:
//
//  1. Is another attempt ALLOWED?
//     Hard rules enforced by AMC / NPCI / lender policy.
//
//  2. Is another attempt WORTHWHILE?
//     Consequence-based urgency: escalate before the point of no return,
//     not after.
//
// If either question returns false, it short-circuits the entire pipeline
// with a product-specific escalation action and consequence_severity tag.
//
// Reference: NACH_Mandate_Recovery_Report.docx §4.3 (Governor Logic)
package nach

import (
	"fmt"

	"razorpay-classification-service/internal/models"
)

// SIP cancellation threshold (AMC rule: 3 consecutive failures → SIP cancelled).
// We escalate at ≥ 2 failures to fire the dunning router BEFORE cancellation,
// not after. This is the tighter timing requirement vs. UPI dunning.
const sipEscalateAtConsecutiveFailures = 2

// SIP hard stop: at exactly 3 failures the AMC will cancel — retry is pointless.
const sipHardStopAtConsecutiveFailures = 3

// EMI credit bureau reporting begins 30 days after due date.
// We escalate at 28 days to give the customer 2 days to act.
const emiCreditRiskEscalateAtDays = 28

// Insurance lapse risk: escalate when any failure is detected (immediate consequence).
const insuranceEscalateAtConsecutiveFailures = 1

// StoppingResult is the output of the NACH stopping policy check.
type StoppingResult struct {
	// ShouldStop is true if the stopping policy has made a determination.
	// When true, the classification pipeline should short-circuit immediately.
	ShouldStop bool

	// Result is the ClassificationResult to persist if ShouldStop is true.
	Result *models.ClassificationResult
}

// Check evaluates the NACH stopping policy for a transaction.
// Returns a StoppingResult; if ShouldStop is false, the pipeline continues normally.
func Check(txn *models.Transaction) StoppingResult {
	// Only applies to NACH rail transactions.
	if txn.PaymentRail != models.PaymentRailNACH {
		return StoppingResult{ShouldStop: false}
	}

	switch txn.ProductType {
	case models.ProductTypeSIP:
		return checkSIP(txn)
	case models.ProductTypeLoanEMI:
		return checkEMI(txn)
	case models.ProductTypeInsurancePremium:
		return checkInsurance(txn)
	default:
		// Unknown product type on NACH rail: fall through to classifier.
		return StoppingResult{ShouldStop: false}
	}
}

// checkSIP enforces the AMC 3-consecutive-failure SIP cancellation rule.
//
// AMC rule: 3 consecutive mandate debit failures → SIP auto-cancelled.
// Our rule: escalate at failure #2 (before the point of no return),
//           hard-stop retry at failure #3 (AMC will cancel regardless).
func checkSIP(txn *models.Transaction) StoppingResult {
	f := txn.ConsecutiveFailureCount

	if f >= sipHardStopAtConsecutiveFailures {
		// AMC will cancel — automatic retry is pointless and wastes a bank attempt.
		mv := "nach-stopping-sip-hard-stop"
		return StoppingResult{
			ShouldStop: true,
			Result: &models.ClassificationResult{
				TransactionID: txn.ID,
				Layer:         0,
				Cause:         models.CauseNACHInsufficientFunds,
				Confidence:    1.0,
				Reasoning: fmt.Sprintf(
					"[Layer 0 · NACH SIP Hard Stop] %d consecutive failures reached the AMC cancellation threshold (%d). "+
						"Automatic retry BLOCKED — further attempts are non-compliant and futile. "+
						"Consequence: investment_lapse_risk. Escalating to dunning router for urgent human-contact.",
					f, sipHardStopAtConsecutiveFailures,
				),
				RecommendedAction: models.ActionSIPCancellationRiskEscalate,
				ModelVersion:      &mv,
			},
		}
	}

	if f >= sipEscalateAtConsecutiveFailures {
		// Pre-emptive escalation: fire dunning router NOW, before failure #3.
		// This is the tighter timing requirement unique to NACH vs. UPI dunning.
		mv := "nach-stopping-sip-pre-emptive-escalate"
		return StoppingResult{
			ShouldStop: true,
			Result: &models.ClassificationResult{
				TransactionID: txn.ID,
				Layer:         0,
				Cause:         models.CauseNACHInsufficientFunds,
				Confidence:    0.95,
				Reasoning: fmt.Sprintf(
					"[Layer 0 · NACH SIP Pre-emptive Escalate] %d consecutive failures detected. "+
						"SIP cancellation threshold is %d — one more failure will trigger AMC auto-cancellation. "+
						"Consequence: investment_lapse_risk. Escalating to dunning router BEFORE the threshold is reached.",
					f, sipHardStopAtConsecutiveFailures,
				),
				RecommendedAction: models.ActionSIPCancellationRiskEscalate,
				ModelVersion:      &mv,
			},
		}
	}

	// Below escalation threshold: fall through to normal classifier.
	return StoppingResult{ShouldStop: false}
}

// checkEMI enforces the EMI credit bureau reporting window.
//
// Credit bureau reporting typically becomes relevant 30 days after due date.
// We escalate at 28 days (2 days before) to give the customer time to act.
// This is factual urgency, not manufactured pressure.
func checkEMI(txn *models.Transaction) StoppingResult {
	if txn.DaysSinceDueDate == nil {
		// No due-date information: fall through to classifier.
		return StoppingResult{ShouldStop: false}
	}

	days := *txn.DaysSinceDueDate

	if days >= emiCreditRiskEscalateAtDays {
		mv := "nach-stopping-emi-credit-risk-escalate"
		return StoppingResult{
			ShouldStop: true,
			Result: &models.ClassificationResult{
				TransactionID: txn.ID,
				Layer:         0,
				Cause:         models.CauseNACHInsufficientFunds,
				Confidence:    1.0,
				Reasoning: fmt.Sprintf(
					"[Layer 0 · NACH EMI Credit Risk] %d days since due date. "+
						"Credit bureau reporting typically begins at 30 days — "+
						"immediate human contact required before payment history is reported. "+
						"Consequence: credit_score_risk. Bypassing retry queue, escalating directly.",
					days,
				),
				RecommendedAction: models.ActionCreditScoreRiskEscalate,
				ModelVersion:      &mv,
			},
		}
	}

	// Under 28 days: classify normally (retry may still be viable).
	return StoppingResult{ShouldStop: false}
}

// checkInsurance escalates immediately on any insurance premium failure.
//
// Insurance policy lapse has immediate, irreversible consequences for the customer:
// coverage terminates and reinstatement may require new underwriting.
// Unlike SIP (3 failures) or EMI (28 days), a single failure justifies urgent contact.
func checkInsurance(txn *models.Transaction) StoppingResult {
	if txn.ConsecutiveFailureCount >= insuranceEscalateAtConsecutiveFailures {
		mv := "nach-stopping-insurance-lapse-escalate"
		return StoppingResult{
			ShouldStop: true,
			Result: &models.ClassificationResult{
				TransactionID: txn.ID,
				Layer:         0,
				Cause:         models.CauseNACHInsufficientFunds,
				Confidence:    0.90,
				Reasoning: fmt.Sprintf(
					"[Layer 0 · NACH Insurance Lapse Risk] %d failure(s) detected on insurance premium mandate. "+
						"Coverage lapse risk is immediate — policy may lapse without prompt payment. "+
						"Consequence: policy_lapse_risk. Escalating to dunning router with high urgency.",
					txn.ConsecutiveFailureCount,
				),
				RecommendedAction: models.ActionPolicyLapseRiskEscalate,
				ModelVersion:      &mv,
			},
		}
	}

	return StoppingResult{ShouldStop: false}
}
