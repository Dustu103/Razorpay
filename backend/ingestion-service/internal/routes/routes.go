package routes

import (
	"razorpay-ingestion-service/internal/handlers"

	"github.com/gofiber/fiber/v2"
)

func Register(app *fiber.App, h *handlers.WebhookHandler, ce *handlers.CheckoutEventHandler) {
	api := app.Group("/api/v1")
	api.Post("/webhook", h.Handle)
	api.Post("/checkout-events", ce.HandleEvent)
}
