package guardrails

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/google/uuid"
)

type ExecutionGuard struct {
	rdb *redis.Client
}

func NewExecutionGuard(rdb *redis.Client) *ExecutionGuard {
	return &ExecutionGuard{rdb: rdb}
}

func (g *ExecutionGuard) Dispatch(sessionID string, diagnosis string, channel string, cartValue float64, message string, risk float64, prob float64, ev float64) {
	ctx := context.Background()
	lockKey := fmt.Sprintf("session:%s:recovery_lock", sessionID)

	// 1. Atomic Lock
	acquired, err := g.rdb.SetNX(ctx, lockKey, "locked", 10*time.Second).Result()
	if err != nil || !acquired {
		log.Printf("[Guard] Could not acquire lock for %s", sessionID)
		return
	}
	
	// 2. Fetch latest status
	status, _ := g.rdb.HGet(ctx, fmt.Sprintf("session:%s", sessionID), "payment_status").Result()
	if status != "pending" {
		log.Printf("[Guard] Aborting %s: payment_status is %s", sessionID, status)
		return
	}
	
	recoveryStatus, _ := g.rdb.HGet(ctx, fmt.Sprintf("session:%s", sessionID), "recovery_status").Result()
	if recoveryStatus != "eligible" {
		log.Printf("[Guard] Aborting %s: recovery_status is %s", sessionID, recoveryStatus)
		return
	}
	
	// 3. Generate Opaque Token (Never expose raw cart in URL)
	recoveryToken := uuid.New().String()
	
	// 4. Update to dispatched
	g.rdb.HSet(ctx, fmt.Sprintf("session:%s", sessionID), "recovery_status", "dispatched")
	
	// 5. Track global metrics for frontend dashboard
	g.rdb.Incr(ctx, "metrics:dropoff:interventions_sent")
	// If channel is not suppressed, add to estimated recovered revenue
	if channel != "NO_ACTION" && channel != "suppressed" {
		g.rdb.IncrByFloat(ctx, "metrics:dropoff:revenue_recovered", cartValue*0.50)
	}

	// 6. Log the action for the live feed, including dual-model telemetry
	timestamp := time.Now().UTC().Format(time.RFC3339)
	actionLog := fmt.Sprintf(`{"session_id":"%s", "diagnosis":"%s", "action":"%s", "timestamp":"%s", "message":"%s", "risk_score":%.3f, "recovery_prob":%.3f, "expected_profit":%.2f}`, 
		sessionID, diagnosis, channel, timestamp, message, risk, prob, ev)
	g.rdb.LPush(ctx, "metrics:dropoff:recent_interventions", actionLog)
	g.rdb.LTrim(ctx, "metrics:dropoff:recent_interventions", 0, 19) // Keep last 20
	
	// In reality, this would send an SNS/Kafka message to the notification service
	log.Printf("[Guard] SUCCESS: Sent recovery link https://rzp.io/r/%s via %s for %s", recoveryToken, channel, sessionID)
	
	// Simulate completion for state machine
	go func() {
		time.Sleep(1 * time.Second)
		g.rdb.HSet(ctx, fmt.Sprintf("session:%s", sessionID), "recovery_status", "completed")
	}()
}
