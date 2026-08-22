package routes

import (
	"razorpay-audit-service/internal/handlers"

	"github.com/gofiber/fiber/v2"
)

func Register(app *fiber.App, h *handlers.ClassificationHandler) {
	api := app.Group("/api/v1")
	api.Get("/classifications", h.List)
	api.Get("/classifications/:id", h.GetByID)
}
