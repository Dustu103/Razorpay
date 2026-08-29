package integration

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/gofiber/fiber/v2"
	"razorpay-bnpl-edge-service/internal/handlers"
)

func TestHandleFallbackOffer_Success(t *testing.T) {
	// 1. Setup mock Python ML Gateway
	mockMLServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"show_bnpl_offer": true, "conversion_probability": 0.95}`))
	}))
	defer mockMLServer.Close()

	os.Setenv("ML_SERVICE_URL", mockMLServer.URL)

	// 2. Setup Fiber App with our handler
	app := fiber.New()
	app.Post("/v1/checkout/fallback-offer", handlers.HandleFallbackOffer)

	// 3. Make test request
	reqBody := []byte(`{"amount": 5000, "decline_reason_encoded": 0, "tenure_months": 24}`)
	req, _ := http.NewRequest(http.MethodPost, "http://localhost/v1/checkout/fallback-offer", bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req, -1)
	if err != nil {
		t.Fatalf("Failed to execute request: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}
}

func TestHandleFallbackOffer_TimeoutFailSilent(t *testing.T) {
	// 1. Setup mock Python ML Gateway that is SLOW (100ms)
	mockMLServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(100 * time.Millisecond) // This violates the 50ms circuit breaker!
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"show_bnpl_offer": true, "conversion_probability": 0.95}`))
	}))
	defer mockMLServer.Close()

	os.Setenv("ML_SERVICE_URL", mockMLServer.URL)

	// 2. Setup Fiber App with our handler
	app := fiber.New()
	app.Post("/v1/checkout/fallback-offer", handlers.HandleFallbackOffer)

	// 3. Make test request
	reqBody := []byte(`{"amount": 5000, "decline_reason_encoded": 0, "tenure_months": 24}`)
	req, _ := http.NewRequest(http.MethodPost, "http://localhost/v1/checkout/fallback-offer", bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")

	start := time.Now()
	resp, err := app.Test(req, -1)
	if err != nil {
		t.Fatalf("Failed to execute request: %v", err)
	}
	duration := time.Since(start)

	// We expect the Edge Gateway to cut the connection and return 503 Service Unavailable
	if resp.StatusCode != http.StatusServiceUnavailable {
		t.Errorf("Expected circuit breaker to trip and return 503, got %d", resp.StatusCode)
	}

	// We expect the Go handler to return quickly (around 50ms), NOT wait the full 100ms
	if duration > 75*time.Millisecond {
		t.Errorf("Expected fail-silent timeout under 75ms, but it took %v", duration)
	}
}
