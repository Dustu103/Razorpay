package main

import (
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"razorpay-bnpl-edge-service/internal/handlers"
)

func main() {
	app := fiber.New(fiber.Config{
		DisableStartupMessage: true,
	})

	app.Post("/v1/checkout/fallback-offer", handlers.HandleFallbackOffer)

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.SendString("OK")
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8003"
	}

	log.Printf("Starting BNPL Edge Service on port %s", port)
	log.Fatal(app.Listen(":" + port))
}
