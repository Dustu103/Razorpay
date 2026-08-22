package main

import (
	"context"
	"log"
	"os"

	"razorpay-audit-service/internal/db"
	"razorpay-audit-service/internal/handlers"
	"razorpay-audit-service/internal/routes"

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
		log.Fatalf("[audit-service] db connect: %v", err)
	}
	defer database.Close()
	log.Println("[audit-service] Postgres connected")

	// ── Fiber ─────────────────────────────────────────────────────────────
	app := fiber.New(fiber.Config{
		AppName:      "Razorpay — Audit Service",
		ErrorHandler: customErrorHandler,
	})

	app.Use(logger.New(), recover.New())
	app.Use(cors.New(cors.Config{
		AllowOrigins: "http://localhost:3000",
		AllowHeaders: "Origin, Content-Type",
		AllowMethods: "GET, OPTIONS",
	}))

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "online", "service": "audit-service"})
	})

	classificationHandler := handlers.NewClassificationHandler(database)
	routes.Register(app, classificationHandler)

	port := os.Getenv("AUDIT_PORT")
	if port == "" {
		port = "3003"
	}
	log.Printf("[audit-service] starting on :%s", port)
	log.Fatal(app.Listen(":" + port))
}

func customErrorHandler(c *fiber.Ctx, err error) error {
	code := fiber.StatusInternalServerError
	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
	}
	return c.Status(code).JSON(fiber.Map{"error": err.Error(), "code": code})
}
