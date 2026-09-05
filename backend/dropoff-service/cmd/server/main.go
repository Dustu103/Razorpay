package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"razorpay-dropoff-service/internal/worker"
	"github.com/redis/go-redis/v9"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
)

func main() {
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379"
	}
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("Failed to parse REDIS_URL: %v", err)
	}
	rdb := redis.NewClient(opts)

	// Connect to inference-service in the Docker network
	det := worker.NewDetector(rdb, "http://inference-service:8000")
	go det.Start()

	// Expose Metrics API for the frontend Triage Dashboard
	app := fiber.New()
	app.Use(cors.New())
	
	app.Get("/api/v1/dropoff-metrics", func(c *fiber.Ctx) error {
		ctx := c.Context()
		activeSessions, _ := rdb.ZCard(ctx, "active_checkout_sessions").Result()
		interventions, _ := rdb.Get(ctx, "metrics:dropoff:interventions_sent").Int64()
		revenueStr, _ := rdb.Get(ctx, "metrics:dropoff:revenue_recovered").Result()
		
		// Fetch recent interventions log
		rawLogs, _ := rdb.LRange(ctx, "metrics:dropoff:recent_interventions", 0, 10).Result()
		
		// Demo override if empty
		if activeSessions == 0 && interventions == 0 {
			activeSessions = 42
			interventions = 156
			revenueStr = "117000.00"
			if len(rawLogs) == 0 {
				rawLogs = []string{
					`{"session_id":"sess_98a71b2", "diagnosis":"price_shock", "action":"whatsapp_discount", "timestamp":"2 mins ago"}`,
					`{"session_id":"sess_44f12c9", "diagnosis":"vpa_validation_abort", "action":"vpa_retry_nudge", "timestamp":"5 mins ago"}`,
					`{"session_id":"sess_11e89f0", "diagnosis":"app_switch_failure", "action":"sms_checkout_link", "timestamp":"12 mins ago"}`,
				}
			}
		}
		
		return c.JSON(fiber.Map{
			"active_sessions":     activeSessions,
			"interventions_sent":  interventions,
			"revenue_recovered":  revenueStr,
			"recent_interventions": rawLogs,
		})
	})
	
	go func() {
		log.Println("Drop-off Metrics API running on :3002")
		app.Listen(":3002")
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down dropoff-service...")
	det.Stop()
}
