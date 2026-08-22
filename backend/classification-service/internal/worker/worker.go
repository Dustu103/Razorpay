// Package worker is the Redis queue consumer for the classification service.
// It runs as a blocking loop: BLPOP from the queue → fetch transaction →
// run Layer 1 → if no match, run Layer 2 stub → persist result.
package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"razorpay-classification-service/internal/db"
	"razorpay-classification-service/internal/layer1"
	"razorpay-classification-service/internal/layer2"
	"razorpay-classification-service/internal/models"

	"github.com/redis/go-redis/v9"
)

const (
	defaultQueueName  = "classification_jobs"
	blockTimeout      = 5 * time.Second // BLPOP timeout before re-polling
	layer2CallTimeout = 30 * time.Second
)

type Worker struct {
	db        *db.DB
	redis     *redis.Client
	queueName string
}

func New(database *db.DB, redisClient *redis.Client) *Worker {
	queueName := os.Getenv("QUEUE_NAME")
	if queueName == "" {
		queueName = defaultQueueName
	}
	return &Worker{db: database, redis: redisClient, queueName: queueName}
}

// Run starts the blocking consumer loop. Call in a goroutine or as main loop.
func (w *Worker) Run(ctx context.Context) {
	log.Printf("[classification-worker] listening on queue=%s", w.queueName)
	for {
		select {
		case <-ctx.Done():
			log.Println("[classification-worker] shutting down")
			return
		default:
		}

		// BLPOP blocks up to blockTimeout waiting for a job
		result, err := w.redis.BLPop(ctx, blockTimeout, w.queueName).Result()
		if err != nil {
			if err == redis.Nil {
				continue // timed out, loop again
			}
			log.Printf("[classification-worker] BLPOP error: %v", err)
			time.Sleep(1 * time.Second)
			continue
		}

		// result[0] = key name, result[1] = payload
		if len(result) < 2 {
			continue
		}

		var job models.ClassificationJob
		if err := json.Unmarshal([]byte(result[1]), &job); err != nil {
			log.Printf("[classification-worker] unmarshal error: %v", err)
			continue
		}

		if err := w.processJob(ctx, job); err != nil {
			log.Printf("[classification-worker] job error txn=%s: %v", job.TransactionID, err)
		}
	}
}

func (w *Worker) processJob(ctx context.Context, job models.ClassificationJob) error {
	// 1. Fetch transaction from DB
	txn, err := w.db.GetTransaction(ctx, job.TransactionID)
	if err != nil {
		return fmt.Errorf("get transaction: %w", err)
	}

	// 2. Layer 1 — deterministic, sub-millisecond
	result := layer1.Classify(txn)

	// 3. Layer 2 — stub classifier (replace with LLM call later)
	if result == nil {
		l2Ctx, cancel := context.WithTimeout(ctx, layer2CallTimeout)
		defer cancel()
		_ = l2Ctx // layer2.Classify doesn't need ctx yet (stub), but real impl will

		result, err = layer2.Classify(txn)
		if err != nil {
			// On Layer 2 failure: fall back to safe default, flag for review
			log.Printf("[classification-worker] layer2 error txn=%s: %v — falling back to soft_decline", txn.ID, err)
			mv := "fallback"
			result = &models.ClassificationResult{
				TransactionID:     txn.ID,
				Layer:             2,
				Cause:             models.CauseSoftDecline,
				Confidence:        0.0,
				Reasoning:         "Classification failed due to an internal error. Defaulted to soft_decline for safe retry. Manual review required.",
				RecommendedAction: models.ActionRetryScheduled,
				ModelVersion:      &mv,
			}
		}
	}

	// 4. Persist classification
	if err := w.db.SaveClassification(ctx, result); err != nil {
		return fmt.Errorf("save classification: %w", err)
	}

	log.Printf("[classification-worker] classified txn=%s → cause=%s layer=%d confidence=%.2f",
		txn.ID, result.Cause, result.Layer, result.Confidence)
	return nil
}
