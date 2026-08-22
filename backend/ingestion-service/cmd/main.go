package main

import (
	"context"
	"log"
	"os"

	"razorpay-ingestion-service/internal/db"
	"razorpay-ingestion-service/internal/handlers"
	"razorpay-ingestion-service/internal/queue"
	"razorpay-ingestion-service/internal/routes"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
)

func main() {
	ctx := context.Background()

	// ── Database ──────────────────────────────────────────────────────────
	database, err := db.Connect(ctx)
	if err != nil {
		log.Fatalf("[ingestion-service] db connect: %v", err)
	}
	defer database.Close()
	log.Println("[ingestion-service] Postgres connected")

	// ── Redis queue ───────────────────────────────────────────────────────
	q, err := queue.New()
	if err != nil {
		log.Fatalf("[ingestion-service] redis connect: %v", err)
	}
	defer q.Close()
	log.Println("[ingestion-service] Redis connected")

	// ── Fiber ─────────────────────────────────────────────────────────────
	app := fiber.New(fiber.Config{
		AppName:      "Razorpay — Ingestion Service",
		ErrorHandler: customErrorHandler,
	})

	app.Use(logger.New(), recover.New())
	app.Use(cors.New(cors.Config{
		AllowOrigins: "http://localhost:3000",
		AllowHeaders: "Origin, Content-Type",
		AllowMethods: "GET, POST, OPTIONS",
	}))

	// Health check
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "online", "service": "ingestion-service"})
	})

	webhookHandler := handlers.NewWebhookHandler(database, q)
	routes.Register(app, webhookHandler)

	port := os.Getenv("INGESTION_PORT")
	if port == "" {
		port = "3001"
	}
	log.Printf("[ingestion-service] starting on :%s", port)
	log.Fatal(app.Listen(":" + port))
}

func customErrorHandler(c *fiber.Ctx, err error) error {
	code := fiber.StatusInternalServerError
	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
	}
	return c.Status(code).JSON(fiber.Map{"error": err.Error(), "code": code})
}
