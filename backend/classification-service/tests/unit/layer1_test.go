package unit

import (
	"testing"
	"time"

	"razorpay-classification-service/internal/layer1"
	"razorpay-classification-service/internal/models"
)

func TestLayer1_Evaluate_ComplianceBlock(t *testing.T) {
	// 1. Missing notification
	txn1 := &models.Transaction{
		ID:                        "txn-1",
		MandateNotificationSentAt: nil,
		DebitScheduledAt:          ptr(time.Now()),
	}

	res1 := layer1.Classify(txn1)
	if res1 == nil || res1.Cause != models.CauseNotificationComplianceBlock {
		t.Errorf("Expected compliance block for missing notification")
	}

	// 2. Late notification (< 24 hours)
	debitAt := time.Now().Add(24 * time.Hour)
	sentAt := debitAt.Add(-20 * time.Hour) // Sent 20 hours before (violation)
	
	txn2 := &models.Transaction{
		ID:                        "txn-2",
		MandateNotificationSentAt: &sentAt,
		DebitScheduledAt:          &debitAt,
	}

	res2 := layer1.Classify(txn2)
	if res2 == nil || res2.Cause != models.CauseNotificationComplianceBlock {
		t.Errorf("Expected compliance block for late notification")
	}
}

func TestLayer1_Evaluate_Pass(t *testing.T) {
	// Valid notification (> 24 hours)
	debitAt := time.Now().Add(48 * time.Hour)
	sentAt := debitAt.Add(-25 * time.Hour)
	
	txn := &models.Transaction{
		ID:                        "txn-3",
		MandateNotificationSentAt: &sentAt,
		DebitScheduledAt:          &debitAt,
	}

	res := layer1.Classify(txn)
	if res != nil {
		t.Errorf("Expected nil result (pass) for valid notification, got %v", res.Cause)
	}
}

func ptr(t time.Time) *time.Time {
	return &t
}
