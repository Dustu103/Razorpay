// Package worker is the Redis queue consumer for the classification service.
// It runs as a blocking loop: BLPOP from the queue → fetch transaction →
// run Layer 1 → if no match, run Layer 2 ML model → persist result.
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
	"razorpay-classification-service/internal/layer3"
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
	sem := make(chan struct{}, 50) // Concurrency limit of 50

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

		sem <- struct{}{}
		go func(j models.ClassificationJob) {
			defer func() { <-sem }()
			if err := w.processJob(ctx, j); err != nil {
				log.Printf("[classification-worker] job error txn=%s: %v", j.TransactionID, err)
			}
		}(job)
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

	// 3 & 4. Mixture of Experts (Layer 2 ML & Layer 3 LLM Concurrently)
	if result == nil {
		type layerResult struct {
			res *models.ClassificationResult
			err error
		}

		l2Chan := make(chan layerResult, 1)
		l3Chan := make(chan layerResult, 1)

		go func() {
			l2Ctx, cancel := context.WithTimeout(ctx, layer2CallTimeout)
			defer cancel()
			_ = l2Ctx
			res, err := layer2.Classify(txn)
			l2Chan <- layerResult{res, err}
		}()

		go func() {
			res, err := layer3.Classify(txn)
			l3Chan <- layerResult{res, err}
		}()

		l2Out := <-l2Chan
		l3Out := <-l3Chan

		if l2Out.err != nil {
			log.Printf("[classification-worker] layer2 error txn=%s: %v", txn.ID, l2Out.err)
			l2Out.res = buildFallbackResult(txn)
		}
		if l3Out.err != nil {
			log.Printf("[classification-worker] layer3 error txn=%s: %v", txn.ID, l3Out.err)
			l3Out.res = buildFallbackResult(txn)
		}

		// Ensemble Logic
		result = &models.ClassificationResult{
			TransactionID: txn.ID,
			Layer:         4, // Layer 4 designates Ensemble Output
		}

		if l2Out.res.Cause == l3Out.res.Cause {
			// Agreement
			result.Cause = l2Out.res.Cause
			result.RecommendedAction = l2Out.res.RecommendedAction
			result.Confidence = 0.99
			result.Reasoning = fmt.Sprintf("[Layer 4 · Ensemble Agreement] ML (Conf: %.2f) and LLM (Conf: %.2f) agreed. %s", l2Out.res.Confidence, l3Out.res.Confidence, l3Out.res.Reasoning)
			mv := "ensemble-agreement"
			result.ModelVersion = &mv
		} else {
			// Disagreement
			if l2Out.res.Confidence >= 0.55 {
				// Trust ML due to high confidence on internal data
				result.Cause = l2Out.res.Cause
				result.RecommendedAction = l2Out.res.RecommendedAction
				result.Confidence = l2Out.res.Confidence
				result.Reasoning = fmt.Sprintf("[Layer 4 · Ensemble ML Override] Disagreement. Trusted ML due to high confidence (%.2f). LLM thought: %s", l2Out.res.Confidence, l3Out.res.Cause)
				mv := "ensemble-ml-override"
				result.ModelVersion = &mv
			} else {
				// Trust LLM as tie-breaker
				result.Cause = l3Out.res.Cause
				result.RecommendedAction = l3Out.res.RecommendedAction
				result.Confidence = l3Out.res.Confidence
				result.Reasoning = fmt.Sprintf("[Layer 4 · Ensemble LLM Tie-break] Disagreement. Trusted LLM due to low ML confidence (%.2f). LLM reasoning: %s", l2Out.res.Confidence, l3Out.res.Reasoning)
				mv := "ensemble-llm-tiebreak"
				result.ModelVersion = &mv
			}
		}
	}

	// ── Post-Ensemble Orchestration (Features B, C, D) ─────────────────────
	// 1. Feature D: False Decline Recovery
	if result.Cause == models.CauseFraudFilterBlock {
		log.Printf("[classification-worker] txn=%s is fraud_filter_block. Evaluating False Decline...", txn.ID)
		likelihood, action, err := layer2.CheckFalseDecline(txn)
		if err == nil {
			result.Reasoning += fmt.Sprintf(" | [Feature D] False Decline Likelihood: %.2f", likelihood)
			if action == models.ActionReverifyReverse {
				result.RecommendedAction = models.ActionReverifyReverse
				log.Printf("[classification-worker] txn=%s OVERRIDE: False Decline detected! Action set to %s", txn.ID, action)
			}
		} else {
			log.Printf("[classification-worker] CheckFalseDecline failed: %v", err)
		}
	}

	// 2. Features B & C: Intelligent Retry & Dunning
	if result.Cause == models.CauseSoftDecline {
		log.Printf("[classification-worker] txn=%s is soft_decline. Evaluating Retry Routing...", txn.ID)
		prob, action, err := layer2.EvaluateRetry(txn)
		if err == nil {
			result.Reasoning += fmt.Sprintf(" | [Feature B] Retry Success Probability: %.2f", prob)
			if action == "retry_scheduled" {
				result.RecommendedAction = models.ActionRetryScheduled
			} else {
				log.Printf("[classification-worker] txn=%s Retry unlikely (%.2f). Evaluating Dunning...", txn.ID, prob)
				// Fallback to Dunning (Feature C)
				dunProb, channel, dErr := layer2.EvaluateDunning(txn)
				if dErr == nil {
					result.Reasoning += fmt.Sprintf(" | [Feature C] Dunning Channel: %s (Prob: %.2f)", channel, dunProb)
					// We'll set the recommended action to trigger a specific dunning channel
					result.RecommendedAction = fmt.Sprintf("trigger_dunning_%s", channel)
				}
			}
		} else {
			log.Printf("[classification-worker] EvaluateRetry failed: %v", err)
		}
	}

	// 5. Persist classification
	if err := w.db.SaveClassification(ctx, result); err != nil {
		return fmt.Errorf("save classification: %w", err)
	}

	log.Printf("[classification-worker] classified txn=%s → cause=%s layer=%d confidence=%.2f action=%s",
		txn.ID, result.Cause, result.Layer, result.Confidence, result.RecommendedAction)
	return nil
}

func buildFallbackResult(txn *models.Transaction) *models.ClassificationResult {
	mv := "fallback"
	return &models.ClassificationResult{
		TransactionID:     txn.ID,
		Layer:             2, // or 3, but this represents a system error
		Cause:             models.CauseSoftDecline,
		Confidence:        0.0,
		Reasoning:         "Classification failed due to an internal error. Defaulted to soft_decline for safe retry. Manual review required.",
		RecommendedAction: models.ActionRetryScheduled,
		ModelVersion:      &mv,
	}
}
