// Package layer1 implements the deterministic RBI notification-compliance check.
// This is a pure function — no DB calls, no external I/O, sub-millisecond.
// Reference: RBI Digital Payments — E-mandate Framework, 2026 (TDD §2.4 & §7.1)
package layer1

import (
	"time"

	"razorpay-classification-service/internal/models"
)

const notificationWindowHours = 24

// Classify checks if a transaction should be classified as a notification
// compliance block (Layer 1). Returns nil if the transaction falls through to Layer 2.
//
// Rule: If mandate_notification_sent_at is null OR was sent less than 24h
// before debit_scheduled_at → compliance block.
func Classify(txn *models.Transaction) *models.ClassificationResult {
	// If debit was not scheduled at all, Layer 1 cannot make a determination.
	if txn.DebitScheduledAt == nil {
		return nil // fall through to Layer 2
	}

	requiredDeadline := txn.DebitScheduledAt.Add(-notificationWindowHours * time.Hour)

	notificationMissed := txn.MandateNotificationSentAt == nil ||
		txn.MandateNotificationSentAt.After(requiredDeadline)

	if notificationMissed {
		return &models.ClassificationResult{
			TransactionID:     txn.ID,
			Layer:             1,
			Cause:             models.CauseNotificationComplianceBlock,
			Confidence:        1.0,
			Reasoning:         "The pre-debit notification was either not sent or was sent less than 24 hours before the scheduled debit, violating the RBI E-mandate Framework 2026 requirement. The debit has been silently rescheduled.",
			RecommendedAction: models.ActionSilentReschedule,
			ModelVersion:      nil, // deterministic — no model used
		}
	}

	return nil // notification was timely — fall through to Layer 2
}
