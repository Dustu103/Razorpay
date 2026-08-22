// Package layer2 is a STUB for the LLM classifier.
// The real implementation will call an LLM API here.
// This stub uses rule-based heuristics on status_code and bank_response_code
// so the full pipeline is functional end-to-end without an LLM key.
package layer2

import (
	"fmt"
	"strings"

	"razorpay-classification-service/internal/models"
)

const stubModelVersion = "stub-v1.0-heuristic"

// Classify is the Layer 2 stub classifier.
// Replace the body of this function with the real LLM call (TDD §3).
func Classify(txn *models.Transaction) (*models.ClassificationResult, error) {
	cause, action, reasoning := heuristicClassify(txn)

	mv := stubModelVersion
	return &models.ClassificationResult{
		TransactionID:     txn.ID,
		Layer:             2,
		Cause:             cause,
		Confidence:        0.75, // stub: fixed confidence until real model is in place
		Reasoning:         reasoning,
		RecommendedAction: action,
		ModelVersion:      &mv,
	}, nil
}

// heuristicClassify is a simple rule table that mimics what the LLM will do.
// It is NOT the production classifier — it exists only to make the pipeline
// testable before the LLM integration is added.
func heuristicClassify(txn *models.Transaction) (cause, action, reasoning string) {
	sc := strings.ToUpper(txn.StatusCode)
	br := ""
	if txn.BankResponseCode != nil {
		br = strings.ToUpper(*txn.BankResponseCode)
	}

	switch {
	// ── Gateway / timeout signals ─────────────────────────────────────────
	case contains(sc, "TIMEOUT", "GATEWAY_ERROR", "TECHNICAL_ERROR", "NETWORK"):
		return models.CauseGatewayFault,
			models.ActionRetryScheduled,
			fmt.Sprintf("Status code '%s' indicates a gateway-level failure unrelated to the customer or issuer. A scheduled retry is appropriate.", txn.StatusCode)

	// ── Fraud / risk signals ──────────────────────────────────────────────
	case contains(br, "59", "14", "57") || contains(sc, "FRAUD", "RISK_CHECK", "BLOCKED"):
		return models.CauseFraudFilterBlock,
			models.ActionDoNotRetry,
			"The bank's response code indicates the transaction was blocked by a fraud or risk filter. Retrying without resolving the underlying flag will continue to fail."

	// ── Hard decline signals (permanent) ─────────────────────────────────
	case contains(br, "05", "12", "41", "43", "54") || contains(sc, "INVALID_CARD", "DO_NOT_HONOUR", "EXPIRED"):
		return models.CauseHardDecline,
			models.ActionDoNotRetry,
			"The issuer has permanently declined this transaction. The card may be expired, blocked, or invalid. The customer should be asked to update their payment method."

	// ── Soft decline (default — retriable) ───────────────────────────────
	default:
		return models.CauseSoftDecline,
			models.ActionRetryScheduled,
			fmt.Sprintf("The failure with status '%s' appears to be a transient soft decline, possibly due to insufficient funds or a temporary issuer issue. A scheduled retry is recommended.", txn.StatusCode)
	}
}

func contains(s string, substrings ...string) bool {
	for _, sub := range substrings {
		if strings.Contains(s, sub) {
			return true
		}
	}
	return false
}
