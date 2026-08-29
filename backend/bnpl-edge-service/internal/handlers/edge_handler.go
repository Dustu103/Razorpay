package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gofiber/fiber/v2"
	"razorpay-bnpl-edge-service/internal/models"
)

var httpClient = &http.Client{
	Timeout: 50 * time.Millisecond, // Ultra-strict latency budget for Edge
}

func HandleFallbackOffer(c *fiber.Ctx) error {
	var req models.CheckoutDeclineRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid JSON"})
	}

	inferenceServiceURL := os.Getenv("ML_SERVICE_URL")
	if inferenceServiceURL == "" {
		inferenceServiceURL = "http://localhost:8000" // Default for local
	}
	mlEndpoint := fmt.Sprintf("%s/predict/checkout-offer", inferenceServiceURL)

	// Prepare payload for ML service
	mlPayload, _ := json.Marshal(req)
	
	// Fire highly optimized network call to Python ML Gateway
	resp, err := httpClient.Post(mlEndpoint, "application/json", bytes.NewBuffer(mlPayload))
	if err != nil {
		log.Printf("Error calling ML service (circuit breaker): %v", err)
		return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{"error": "ML Service unavailable or timed out"})
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("ML Service returned status code: %d", resp.StatusCode)
		return c.Status(fiber.StatusBadGateway).JSON(fiber.Map{"error": "ML Service returned error"})
	}

	body, _ := io.ReadAll(resp.Body)
	var mlResp models.FallbackOfferResponse
	if err := json.Unmarshal(body, &mlResp); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to parse ML response"})
	}

	return c.JSON(mlResp)
}
