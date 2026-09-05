package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"

	"razorpay-nach-recovery-service/internal/db"
	"razorpay-nach-recovery-service/internal/models"
	"razorpay-nach-recovery-service/internal/worker"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	// ── Database (Optional/Graceful for standalone testing) ───────────────
	var database *db.DB
	database, err := db.Connect(ctx)
	if err != nil {
		log.Printf("[nach-recovery-service] WARNING: Postgres connect failed (%v). Running with in-memory state.", err)
	} else {
		defer database.Close()
		log.Println("[nach-recovery-service] Postgres connected successfully.")
	}

	// ── Background Recovery Worker ─────────────────────────────────────────
	w := worker.New(database)
	w.Start(ctx)
	defer w.Stop()

	// ── Fiber HTTP Server ──────────────────────────────────────────────────
	app := fiber.New(fiber.Config{
		AppName: "Razorpay — NACH Mandate Recovery Service",
	})

	app.Use(cors.New(), logger.New(), recover.New())

	// Healthcheck endpoint
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status":  "online",
			"service": "nach-recovery-service",
			"port":    "3007",
		})
	})

	// Telemetry & Metrics endpoint for Dashboard
	app.Get("/api/v1/nach-metrics", func(c *fiber.Ctx) error {
		metrics := w.GetMetrics()
		return c.JSON(metrics)
	})

	// Synchronous single-mandate evaluation endpoint
	app.Post("/api/v1/evaluate-mandate", func(c *fiber.Ctx) error {
		var req models.EvaluationRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Invalid request payload: " + err.Error(),
			})
		}

		decision := w.Evaluate(&req)
		return c.JSON(decision)
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "3007"
	}

	go func() {
		log.Printf("[nach-recovery-service] Starting HTTP server on :%s", port)
		if err := app.Listen(":" + port); err != nil {
			log.Fatalf("[nach-recovery-service] Fiber listen error: %v", err)
		}
	}()

	<-ctx.Done()
	log.Println("[nach-recovery-service] Shutting down gracefully...")
}
