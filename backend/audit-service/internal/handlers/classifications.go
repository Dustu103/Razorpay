package handlers

import (
	"context"
	"strconv"

	"razorpay-audit-service/internal/db"
	"razorpay-audit-service/internal/models"

	"github.com/gofiber/fiber/v2"
)

type ClassificationHandler struct {
	db *db.DB
}

func NewClassificationHandler(database *db.DB) *ClassificationHandler {
	return &ClassificationHandler{db: database}
}

// List handles GET /api/v1/classifications
// Query params: cause, layer, limit, offset
func (h *ClassificationHandler) List(c *fiber.Ctx) error {
	filter := models.ListFilter{
		Cause: c.Query("cause"),
	}
	if layerStr := c.Query("layer"); layerStr != "" {
		l, err := strconv.Atoi(layerStr)
		if err == nil && (l == 1 || l == 2) {
			filter.Layer = &l
		}
	}
	filter.Limit, _ = strconv.Atoi(c.Query("limit", "50"))
	filter.Offset, _ = strconv.Atoi(c.Query("offset", "0"))

	results, err := h.db.ListClassifications(context.Background(), filter)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.ErrorResponse{
			Error: err.Error(), Code: "DB_ERROR",
		})
	}
	if results == nil {
		results = []models.ClassificationView{}
	}
	return c.JSON(fiber.Map{"data": results, "count": len(results)})
}

// GetByID handles GET /api/v1/classifications/:id
func (h *ClassificationHandler) GetByID(c *fiber.Ctx) error {
	id := c.Params("id")
	if id == "" {
		return c.Status(fiber.StatusBadRequest).JSON(models.ErrorResponse{
			Error: "id is required", Code: "MISSING_ID",
		})
	}

	result, err := h.db.GetClassification(context.Background(), id)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(models.ErrorResponse{
			Error: err.Error(), Code: "NOT_FOUND",
		})
	}
	return c.JSON(result)
}
