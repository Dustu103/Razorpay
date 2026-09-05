package worker

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"razorpay-dropoff-service/internal/guardrails"
	"github.com/redis/go-redis/v9"
)

type Detector struct {
	rdb         *redis.Client
	mlURL       string
	stopChan    chan struct{}
	guardrails  *guardrails.ExecutionGuard
}

func NewDetector(rdb *redis.Client, mlURL string) *Detector {
	return &Detector{
		rdb:        rdb,
		mlURL:      mlURL,
		stopChan:   make(chan struct{}),
		guardrails: guardrails.NewExecutionGuard(rdb),
	}
}

func (d *Detector) Start() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	log.Println("Detector started polling active_checkout_sessions...")
	for {
		select {
		case <-ticker.C:
			d.processExpiredSessions()
		case <-d.stopChan:
			return
		}
	}
}

func (d *Detector) Stop() {
	close(d.stopChan)
}

func (d *Detector) processExpiredSessions() {
	ctx := context.Background()
	now := float64(time.Now().UTC().Unix())

	// ZRANGEBYSCORE active_checkout_sessions -inf <now>
	sessions, err := d.rdb.ZRangeByScore(ctx, "active_checkout_sessions", &redis.ZRangeBy{
		Min: "-inf",
		Max: fmt.Sprintf("%f", now),
	}).Result()

	if err != nil {
		log.Printf("[Detector] Error fetching sessions: %v", err)
		return
	}

	for _, sessionID := range sessions {
		// Remove to prevent other workers from picking it up immediately
		removed, err := d.rdb.ZRem(ctx, "active_checkout_sessions", sessionID).Result()
		if err != nil || removed == 0 {
			continue // Another worker got it
		}
		
		go d.evaluateSession(sessionID)
	}
}

func (d *Detector) evaluateSession(sessionID string) {
	ctx := context.Background()
	log.Printf("[Detector] Evaluating expired session: %s", sessionID)

	// Fetch Session Hash
	hash, err := d.rdb.HGetAll(ctx, fmt.Sprintf("session:%s", sessionID)).Result()
	if err != nil || len(hash) == 0 {
		return
	}

	if hash["payment_status"] != "pending" {
		log.Printf("[Detector] Session %s already resolved: %s", sessionID, hash["payment_status"])
		return
	}

	// ── Parse Event Stream — extract ALL behavioral signals ───────────────────
	eventsRaw, _ := d.rdb.LRange(ctx, fmt.Sprintf("session:%s:events", sessionID), 0, -1).Result()
	
	hasRedirectInit := false
	hasRedirectRet  := false
	hasOtpSent      := false
	hasOtpEnt       := false
	hasVpaFailed    := false
	hasCartViewed   := false

	var eventTypes []string
	var cartValue  float64 = 0.0
	var attemptCount int   = 0
	startTime      := time.Now()
	firstEventTime := time.Time{}
	
	for _, raw := range eventsRaw {
		var ev map[string]interface{}
		if json.Unmarshal([]byte(raw), &ev) != nil {
			continue
		}
		
		evType := ""
		if t, ok := ev["event_type"].(string); ok {
			evType = t
		}
		eventTypes = append(eventTypes, evType)

		// Parse timestamp for session duration and timing features
		if ts, ok := ev["timestamp"].(string); ok {
			if t, err := time.Parse(time.RFC3339, ts); err == nil {
				if firstEventTime.IsZero() {
					firstEventTime = t
				}
				startTime = t
			}
		}

		// Extract economic features
		if evType == "cart_breakdown_viewed" || evType == "cart_viewed" {
			if v, ok := ev["cart_value"].(float64); ok && v > 0 {
				cartValue = v
			}
		}

		// Track retry velocity
		if evType == "payment_attempted" || evType == "redirect_initiated" {
			attemptCount++
		}

		switch evType {
		case "redirect_initiated": hasRedirectInit = true
		case "redirect_returned": hasRedirectRet = true
		case "otp_sent": hasOtpSent = true
		case "otp_entered": hasOtpEnt = true
		case "vpa_validation_failed": hasVpaFailed = true
		case "cart_breakdown_viewed": hasCartViewed = true
		}
		_ = startTime
	}

	// Compute session duration
	durationSec := 45 // default fallback
	if !firstEventTime.IsZero() {
		durationSec = int(time.Since(firstEventTime).Seconds())
	}

	if attemptCount == 0 {
		attemptCount = 1
	}

	// Fallback to session hash if cart_value wasn't in events
	if cartValue == 0.0 {
		if v, ok := hash["cart_value"]; ok {
			fmt.Sscanf(v, "%f", &cartValue)
		}
		if cartValue == 0.0 {
			cartValue = 1500.00 // last-resort default
		}
	}

	// ── Deterministic Diagnosis ────────────────────────────────────────────────
	diagnosis := "genuine_abandonment"
	if hasRedirectInit && !hasRedirectRet {
		diagnosis = "app_switch_failure"
	} else if hasOtpSent && !hasOtpEnt {
		diagnosis = "otp_delivery_delay"
	} else if hasVpaFailed {
		diagnosis = "vpa_validation_abort"
	} else if hasCartViewed {
		diagnosis = "price_shock"
	}
	
	// Pass to Python for EV scoring & Risk gating (Two-Stage ML)
	// We join eventTypes with commas so Python can calculate sequence_entropy
	eventSequence := strings.Join(eventTypes, ",")

	reqBody, _ := json.Marshal(map[string]interface{}{
		"session_id":       sessionID,
		"diagnosis":        diagnosis,
		"cart_value":       cartValue,
		"duration_sec":     durationSec,
		"attempt_count":    attemptCount,
		"events_count":     len(eventsRaw),
		"event_sequence":   eventSequence,
		"merchant_name":    hash["merchant_name"],
		"item_description": hash["item_description"],
	})
	
	resp, err := http.Post(d.mlURL+"/predict/intervention", "application/json", bytes.NewBuffer(reqBody))
	if err != nil || resp.StatusCode != 200 {
		log.Printf("[Detector] ML inference failed or unavailable for %s: %v", sessionID, err)
		return
	}
	
	var mlResult struct {
		Action          string  `json:"action"`            // NO_ACTION, SMS, WHATSAPP
		RiskScore       float64 `json:"risk_score"`
		RecoveryProb    float64 `json:"recovery_prob"`
		ExpectedProfit  float64 `json:"expected_profit"`
		RecoveryMessage string  `json:"recovery_message"`
	}
	json.NewDecoder(resp.Body).Decode(&mlResult)
	resp.Body.Close()
	
	if mlResult.Action != "NO_ACTION" && mlResult.Action != "" {
		log.Printf("[Detector] Dispatching recovery for %s via %s (Profit: ₹%.2f, Risk: %.2f)", sessionID, mlResult.Action, mlResult.ExpectedProfit, mlResult.RiskScore)
		// We pass all telemetry to Dispatch
		d.guardrails.Dispatch(sessionID, diagnosis, mlResult.Action, cartValue, mlResult.RecoveryMessage, mlResult.RiskScore, mlResult.RecoveryProb, mlResult.ExpectedProfit)
	} else {
		log.Printf("[Detector] Suppressed %s (Risk: %.2f, Profit: ₹%.2f)", sessionID, mlResult.RiskScore, mlResult.ExpectedProfit)
		d.rdb.HSet(ctx, fmt.Sprintf("session:%s", sessionID), "recovery_status", "suppressed")
	}
}
