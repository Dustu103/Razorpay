package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"razorpay-b2b-recovery-service/internal/db"
	"razorpay-b2b-recovery-service/internal/worker"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	// ── Database ──────────────────────────────────────────────────────────
	database, err := db.Connect(ctx)
	if err != nil {
		log.Fatalf("[b2b-recovery-service] db connect: %v", err)
	}
	defer database.Close()
	log.Println("[b2b-recovery-service] Postgres connected")

	// ── Cron Worker ───────────────────────────────────────────────────────
	w := worker.New(database)
	w.Start(ctx)
	defer w.Stop()

	// ── Fiber (Healthcheck) ───────────────────────────────────────────────
	app := fiber.New(fiber.Config{
		AppName: "Razorpay — B2B Recovery Service",
	})

	app.Use(logger.New(), recover.New())

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "online", "service": "b2b-recovery-service"})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "3006" // Assigning a unique port for b2b-recovery-service
	}

	go func() {
		log.Printf("[b2b-recovery-service] starting health server on :%s", port)
		if err := app.Listen(":" + port); err != nil {
			log.Fatalf("[b2b-recovery-service] fiber listen error: %v", err)
		}
	}()

	// Block until signal received
	<-ctx.Done()
	log.Println("[b2b-recovery-service] shutting down...")
	app.Shutdown()
}
