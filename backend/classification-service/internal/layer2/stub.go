package layer2

import (
	"math/rand"
	"strings"

	"razorpay-classification-service/internal/models"
)

const stubModelVersion = "qwen2.5-7b-finetuned-sim"

// Classify simulates a fast, fine-tuned text classifier.
// It returns a classification with a dynamic confidence score based on the clarity of the signals.
// It does not return verbose generative reasoning, only a categorical reason.
func Classify(txn *models.Transaction) (*models.ClassificationResult, error) {
	cause, action, reasonCode, baseConfidence := heuristicClassify(txn)

	// Add some jitter to the confidence to simulate real model uncertainty
	jitter := (rand.Float64() * 0.2) - 0.1 // +/- 10%
	confidence := baseConfidence + jitter
	if confidence > 0.99 {
		confidence = 0.99
	}
	if confidence < 0.1 {
		confidence = 0.1
	}

	mv := stubModelVersion
	return &models.ClassificationResult{
		TransactionID:     txn.ID,
		Layer:             2,
		Cause:             cause,
		Confidence:        confidence,
		Reasoning:         reasonCode,
		RecommendedAction: action,
		ModelVersion:      &mv,
	}, nil
}

// heuristicClassify returns the cause, action, reasoning code, and a base confidence.
func heuristicClassify(txn *models.Transaction) (string, string, string, float64) {
	sc := strings.ToUpper(txn.StatusCode)
	br := ""
	if txn.BankResponseCode != nil {
		br = strings.ToUpper(*txn.BankResponseCode)
	}

	switch {
	case contains(br, "99") && txn.Amount > 50000:
		// Simulated edge case that confuses Layer 2 (should trigger Layer 3 fallback)
		// We return reverify_and_reverse but with very low confidence so the worker kicks it to L3.
		return models.CauseFraudFilterBlock, models.ActionReverifyReverse, "L2_ANOMALY_99", 0.60

	case contains(sc, "TIMEOUT", "GATEWAY_ERROR", "TECHNICAL_ERROR", "NETWORK"):
		return models.CauseGatewayFault, models.ActionRetryScheduled, "L2_GATEWAY_FAULT_MATCH", 0.90

	case contains(br, "59", "14", "57") || contains(sc, "FRAUD", "RISK_CHECK", "BLOCKED"):
		return models.CauseFraudFilterBlock, models.ActionDoNotRetry, "L2_FRAUD_SIGNAL_MATCH", 0.85

	case contains(br, "05", "12", "41", "43", "54") || contains(sc, "INVALID_CARD", "DO_NOT_HONOUR", "EXPIRED"):
		return models.CauseHardDecline, models.ActionDoNotRetry, "L2_HARD_DECLINE_MATCH", 0.92

	default:
		// Default soft decline, medium confidence
		return models.CauseSoftDecline, models.ActionRetryScheduled, "L2_DEFAULT_SOFT", 0.70
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
