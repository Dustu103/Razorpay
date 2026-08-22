package handlers

import (
	"context"
	"log"
	"strings"
	"time"

	"razorpay-ingestion-service/internal/db"
	"razorpay-ingestion-service/internal/models"
	"razorpay-ingestion-service/internal/queue"

	"github.com/gofiber/fiber/v2"
)

type WebhookHandler struct {
	db    *db.DB
	queue *queue.Queue
}

func NewWebhookHandler(database *db.DB, q *queue.Queue) *WebhookHandler {
	return &WebhookHandler{db: database, queue: q}
}

// Handle receives a Razorpay payment.failed webhook, deduplicates it,
// persists the transaction, and enqueues a classification job.
func (h *WebhookHandler) Handle(c *fiber.Ctx) error {
	var payload models.WebhookPayload
	if err := c.BodyParser(&payload); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error: "invalid JSON body",
			Code:  "INVALID_BODY",
		})
	}

	pd := payload.Payload.Payment.Entity

	// ── Data cleaning (Section 5 of TDD) ──────────────────────────────────
	pd.StatusCode = strings.ToUpper(strings.TrimSpace(pd.StatusCode))
	pd.StatusCode = normaliseStatusCode(pd.StatusCode)

	if pd.RetryCount < 0 || pd.RetryCount > 10 {
		log.Printf("[ingestion] unusual retry_count=%d for txn=%s — clamped", pd.RetryCount, pd.ID)
		pd.RetryCount = min(max(pd.RetryCount, 0), 10)
	}

	// Parse optional timestamps — preserve null as null (TDD §5.1)
	var mandateSentAt, debitAt *time.Time
	if pd.MandateNotificationSentAt != nil {
		t, err := time.Parse(time.RFC3339, *pd.MandateNotificationSentAt)
		if err == nil {
			mandateSentAt = &t
		}
	}
	if pd.DebitScheduledAt != nil {
		t, err := time.Parse(time.RFC3339, *pd.DebitScheduledAt)
		if err == nil {
			debitAt = &t
		}
	}

	txn := &models.Transaction{
		GatewayTransactionID:      pd.ID,
		StatusCode:                pd.StatusCode,
		NPCIResponseCode:          pd.NPCIResponseCode,
		BankResponseCode:          pd.BankResponseCode,
		Amount:                    pd.Amount,
		CustomerBank:              pd.Bank,
		RetryCountSoFar:           pd.RetryCount,
		MandateNotificationSentAt: mandateSentAt,
		DebitScheduledAt:          debitAt,
	}

	ctx := context.Background()

	// ── Atomic upsert (TDD §2.3) ──────────────────────────────────────────
	id, isNew, err := h.db.UpsertTransaction(ctx, txn)
	if err != nil {
		log.Printf("[ingestion] db upsert error: %v", err)
		return c.Status(fiber.StatusInternalServerError).JSON(models.ErrorResponse{
			Error: "failed to persist transaction",
			Code:  "DB_ERROR",
		})
	}
	if !isNew {
		// Duplicate webhook — acknowledge without re-processing
		log.Printf("[ingestion] duplicate webhook for txn=%s — dropped", pd.ID)
		return c.Status(fiber.StatusOK).JSON(fiber.Map{
			"status": "duplicate",
			"message": "already ingested",
		})
	}

	// ── Enqueue classification job ─────────────────────────────────────────
	job := models.ClassificationJob{TransactionID: id}
	if err := h.queue.Enqueue(ctx, job); err != nil {
		log.Printf("[ingestion] enqueue error: %v", err)
		return c.Status(fiber.StatusInternalServerError).JSON(models.ErrorResponse{
			Error: "failed to enqueue job",
			Code:  "QUEUE_ERROR",
		})
	}

	log.Printf("[ingestion] ingested txn=%s id=%s", pd.ID, id)
	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"status":         "accepted",
		"transaction_id": id,
	})
}

// normaliseStatusCode maps gateway-specific synonyms to canonical values (TDD §5.1).
func normaliseStatusCode(code string) string {
	synonyms := map[string]string{
		"TIMED_OUT":    "TIMEOUT",
		"TIME_OUT":     "TIMEOUT",
		"DECLINED":     "FAILED",
		"CARD_DECLINE": "FAILED",
	}
	if canonical, ok := synonyms[code]; ok {
		return canonical
	}
	return code
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
