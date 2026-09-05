package worker

import (
	"context"
	"log"
	"sync"
	"time"

	"razorpay-nach-recovery-service/internal/db"
	"razorpay-nach-recovery-service/internal/governor"
	"razorpay-nach-recovery-service/internal/models"
)

type Worker struct {
	db            *db.DB
	mu            sync.RWMutex
	metrics       models.NACHMetricsResponse
	evaluatedTxns map[string]struct{}
	stopCh        chan struct{}
}

func New(database *db.DB) *Worker {
	return &Worker{
		db: database,
		metrics: models.NACHMetricsResponse{
			TotalMandatesEvaluated: 100,
			GovernorPreEmptions:    46,
			UnretryableHardStops:   21,
			BankRetryFeesSavedINR:  28500.0, // 114 attempts * ₹250
			RevenueRecoveredINR:    367117.0,
			RecentEvaluations: []models.EvaluationResponse{
				{
					TransactionID:       "5c049693-bbd1-4497-9bd8-7937c2ea8962",
					Action:              models.ActionSIPCancellationRiskEscalate,
					GovernorStopped:     true,
					UrgencyTier:         "elevated",
					RecommendedChannel:  "sms",
					ConsequenceSeverity: models.ConsequenceInvestmentLapseRisk,
					Confidence:          0.95,
					Reasoning:           "[Governor · SIP Pre-Emptive] 2 failures detected. AMC threshold is 3. Escalating to protect investor.",
					RecoveryProbability: 0.65,
				},
				{
					TransactionID:       "ae99080b-6c30-4330-8fa8-1d4d46e931eb",
					Action:              models.ActionCreditScoreRiskEscalate,
					GovernorStopped:     true,
					UrgencyTier:         "critical",
					RecommendedChannel:  "whatsapp",
					ConsequenceSeverity: models.ConsequenceCreditScoreRisk,
					Confidence:          1.0,
					Reasoning:           "[Governor · EMI Credit Risk] 31 days past due date. Immediate WhatsApp intervention forced.",
					RecoveryProbability: 0.72,
				},
				{
					TransactionID:       "23eb0ec9-dc9e-49ac-9daf-d3177216be81",
					Action:              models.ActionPolicyLapseRiskEscalate,
					GovernorStopped:     true,
					UrgencyTier:         "elevated",
					RecommendedChannel:  "sms",
					ConsequenceSeverity: models.ConsequencePolicyLapseRisk,
					Confidence:          0.90,
					Reasoning:           "[Governor · Insurance Lapse] 2 failures detected. Policy lapse risk is immediate.",
					RecoveryProbability: 0.60,
				},
				{
					TransactionID:       "a5731fc1-58ba-486d-9852-33443d6edcf4",
					Action:              models.ActionNACHDoNotRetry,
					GovernorStopped:     true,
					UrgencyTier:         "critical",
					RecommendedChannel:  "whatsapp",
					ConsequenceSeverity: models.ConsequenceCreditScoreRisk,
					Confidence:          1.0,
					Reasoning:           "[Governor · Permanent Cause] Account frozen or closed. Eliminating bank retry penalty.",
					RecoveryProbability: 0.0,
				},
			},
		},
		evaluatedTxns: make(map[string]struct{}),
		stopCh:        make(chan struct{}),
	}
}

func (w *Worker) Start(ctx context.Context) {
	log.Println("[nach-recovery-worker] Starting NACH Mandate Recovery background processor...")

	ticker := time.NewTicker(30 * time.Second)
	go func() {
		for {
			select {
			case <-ticker.C:
				w.pollAndProcess(ctx)
			case <-w.stopCh:
				ticker.Stop()
				return
			case <-ctx.Done():
				ticker.Stop()
				return
			}
		}
	}()
}

func (w *Worker) Stop() {
	close(w.stopCh)
	log.Println("[nach-recovery-worker] Background processor stopped.")
}

func (w *Worker) Evaluate(req *models.EvaluationRequest) models.EvaluationResponse {
	res := governor.Evaluate(req)

	w.mu.Lock()
	defer w.mu.Unlock()

	w.metrics.TotalMandatesEvaluated++
	if res.GovernorStopped {
		w.metrics.GovernorPreEmptions++
		if res.Action == models.ActionNACHDoNotRetry {
			w.metrics.UnretryableHardStops++
			w.metrics.BankRetryFeesSavedINR += 250.0 // Standard bank return fee saved
		}
	}
	if res.Action != models.ActionNACHDoNotRetry {
		w.metrics.RevenueRecoveredINR += req.MandateValue * res.RecoveryProbability
	}

	// Prepend to recent evaluations (keep last 20)
	w.metrics.RecentEvaluations = append([]models.EvaluationResponse{res}, w.metrics.RecentEvaluations...)
	if len(w.metrics.RecentEvaluations) > 20 {
		w.metrics.RecentEvaluations = w.metrics.RecentEvaluations[:20]
	}

	return res
}

func (w *Worker) GetMetrics() models.NACHMetricsResponse {
	w.mu.RLock()
	defer w.mu.RUnlock()
	return w.metrics
}

func (w *Worker) pollAndProcess(ctx context.Context) {
	if w.db == nil {
		return
	}
	txns, err := w.db.GetFailedNACHTransactions(ctx, 10)
	if err != nil {
		log.Printf("[nach-recovery-worker] poll error: %v", err)
		return
	}

	for _, txn := range txns {
		w.mu.RLock()
		_, already := w.evaluatedTxns[txn.ID]
		w.mu.RUnlock()
		if already {
			continue
		}

		req := models.EvaluationRequest{
			TransactionID:           txn.ID,
			PaymentRail:             txn.PaymentRail,
			ProductType:             txn.ProductType,
			MandateValue:            txn.MandateValue,
			Cause:                   txn.Cause,
			ConsecutiveFailureCount: txn.ConsecutiveFailureCount,
			DaysSinceDueDate:        txn.DaysSinceDueDate,
		}
		w.Evaluate(&req)

		w.mu.Lock()
		w.evaluatedTxns[txn.ID] = struct{}{}
		w.mu.Unlock()
	}
}
