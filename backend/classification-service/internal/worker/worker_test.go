package worker

import (
	"testing"

	"razorpay-classification-service/internal/models"
)

func TestBuildFallbackResult(t *testing.T) {
	txn := &models.Transaction{
		ID: "txn-fallback",
	}

	res := buildFallbackResult(txn)

	if res.TransactionID != "txn-fallback" {
		t.Errorf("Expected transaction ID to match, got %s", res.TransactionID)
	}
	if res.Layer != 2 {
		t.Errorf("Expected Layer 2 for global fallback, got %d", res.Layer)
	}
	if res.Cause != models.CauseSoftDecline {
		t.Errorf("Expected safe fallback cause to be soft_decline, got %s", res.Cause)
	}
	if res.RecommendedAction != models.ActionRetryScheduled {
		t.Errorf("Expected safe fallback action to be retry_scheduled, got %s", res.RecommendedAction)
	}
	if res.Confidence != 0.0 {
		t.Errorf("Expected 0.0 confidence for global fallback, got %f", res.Confidence)
	}
}
