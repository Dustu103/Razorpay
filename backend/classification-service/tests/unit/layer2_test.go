package unit

import (
	"testing"

	"razorpay-classification-service/internal/layer2"
	"razorpay-classification-service/internal/models"
)

func TestLayer2_Classify_FraudBlock(t *testing.T) {
	brc := "57"
	txn := &models.Transaction{
		ID:               "txn-l2-1",
		BankResponseCode: &brc,
	}

	res, _ := layer2.Classify(txn)
	if res.Cause != models.CauseFraudFilterBlock {
		t.Errorf("Expected fraud block for bank code 57, got %s", res.Cause)
	}
	if res.RecommendedAction != models.ActionDoNotRetry && res.RecommendedAction != models.ActionReverifyReverse {
		t.Errorf("Expected do_not_retry or reverify_and_reverse for fraud block, got %s", res.RecommendedAction)
	}
	if res.Confidence < 0.0 || res.Confidence > 1.0 {
		t.Errorf("Confidence out of bounds: %f", res.Confidence)
	}
}

func TestLayer2_Classify_GatewayFault(t *testing.T) {
	txn := &models.Transaction{
		ID:         "txn-l2-2",
		StatusCode: "GATEWAY_ERROR",
	}

	res, _ := layer2.Classify(txn)
	if res.Cause != models.CauseGatewayFault {
		t.Errorf("Expected gateway fault, got %s", res.Cause)
	}
	if res.RecommendedAction != models.ActionRetryScheduled && res.RecommendedAction != models.ActionRetryNow {
		t.Errorf("Expected retry action, got %s", res.RecommendedAction)
	}
}
