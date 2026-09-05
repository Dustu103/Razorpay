package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/redis/go-redis/v9"
)

type CheckoutEventHandler struct {
	rdb *redis.Client
}

func NewCheckoutEventHandler(rdb *redis.Client) *CheckoutEventHandler {
	return &CheckoutEventHandler{rdb: rdb}
}

type CheckoutEvent struct {
	EventID         string  `json:"event_id"`
	SessionID       string  `json:"session_id"`
	EventType       string  `json:"event_type"`
	ClientTimestamp string  `json:"client_timestamp"`
	CartValue       float64 `json:"cart_value,omitempty"`
}

func (h *CheckoutEventHandler) HandleEvent(c *fiber.Ctx) error {
	var event CheckoutEvent
	if err := c.BodyParser(&event); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid JSON body"})
	}

	ctx := context.Background()
	serverTimestamp := time.Now().UTC().Format(time.RFC3339)

	// 1. Idempotency Check via event_id
	isNew, err := h.rdb.SAdd(ctx, fmt.Sprintf("session:%s:processed_events", event.SessionID), event.EventID).Result()
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "redis error"})
	}
	if isNew == 0 {
		return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "duplicate", "message": "event already processed"})
	}

	// 2. Persist event to timeline
	eventJSON, _ := json.Marshal(map[string]interface{}{
		"event_id":         event.EventID,
		"event_type":       event.EventType,
		"client_timestamp": event.ClientTimestamp,
		"server_timestamp": serverTimestamp,
		"cart_value":       event.CartValue,
	})
	
	h.rdb.RPush(ctx, fmt.Sprintf("session:%s:events", event.SessionID), eventJSON)
	
	// 3. Update Session Hash state
	h.rdb.HSet(ctx, fmt.Sprintf("session:%s", event.SessionID), map[string]interface{}{
		"current_step":   event.EventType,
		"last_event_at":  event.ClientTimestamp,
		"payment_status": "pending", // assume pending until terminal event
	})
	// Only set recovery_status if it doesn't exist
	h.rdb.HSetNX(ctx, fmt.Sprintf("session:%s", event.SessionID), "recovery_status", "eligible")
	
	// 4. Calculate dynamic deadline
	var deadline time.Time
	clientTime, err := time.Parse(time.RFC3339, event.ClientTimestamp)
	if err != nil {
		clientTime = time.Now().UTC()
	}
	
	switch event.EventType {
	case "redirect_initiated":
		deadline = clientTime.Add(120 * time.Second) // 2 mins for UPI
	case "otp_sent":
		deadline = clientTime.Add(60 * time.Second) // 1 min for OTP
	case "payment_success", "payment_failed", "checkout_closed":
		// Terminal event: explicitly drop from ZSET and update state
		h.rdb.ZRem(ctx, "active_checkout_sessions", event.SessionID)
		h.rdb.HSet(ctx, fmt.Sprintf("session:%s", event.SessionID), "payment_status", event.EventType)
		
		// Set quick expiration to clean up terminal sessions
		expiration := 2 * time.Hour
		h.rdb.Expire(ctx, fmt.Sprintf("session:%s", event.SessionID), expiration)
		h.rdb.Expire(ctx, fmt.Sprintf("session:%s:events", event.SessionID), expiration)
		h.rdb.Expire(ctx, fmt.Sprintf("session:%s:processed_events", event.SessionID), expiration)
		
		return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "terminal_recorded"})
	default:
		deadline = clientTime.Add(300 * time.Second) // default 5 mins
	}
	
	// 5. Update ZSET
	h.rdb.ZAdd(ctx, "active_checkout_sessions", redis.Z{
		Score:  float64(deadline.Unix()),
		Member: event.SessionID,
	})
	
	// 6. Set general TTLs
	expiration := 2 * time.Hour
	h.rdb.Expire(ctx, fmt.Sprintf("session:%s", event.SessionID), expiration)
	h.rdb.Expire(ctx, fmt.Sprintf("session:%s:events", event.SessionID), expiration)
	h.rdb.Expire(ctx, fmt.Sprintf("session:%s:processed_events", event.SessionID), expiration)

	return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "accepted"})
}
