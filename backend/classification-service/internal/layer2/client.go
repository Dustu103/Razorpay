package layer2

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"razorpay-classification-service/internal/models"
)

var httpClient = &http.Client{
	Timeout: 2 * time.Second,
}

// Classify makes an HTTP POST request to the Python ml-service.
func Classify(txn *models.Transaction) (*models.ClassificationResult, error) {
	mlURL := os.Getenv("ML_SERVICE_URL")
	if mlURL == "" {
		mlURL = "http://localhost:8000"
	}
	
	endpoint := fmt.Sprintf("%s/predict", mlURL)

	// Map Go struct to the JSON schema expected by the Python ML service
	type MLPayload struct {
		ID                        string `json:"id"`
		StatusCode                string `json:"status_code"`
		BankResponseCode          string `json:"bank_response_code,omitempty"`
		NPCIResponseCode          string `json:"npci_response_code,omitempty"`
		AmountPaise               int    `json:"amount_paise"`
		IssuerBank                string `json:"issuer_bank,omitempty"`
		RetryCountSoFar           int    `json:"retry_count_so_far"`
	}

	payload := MLPayload{
		ID:              txn.ID,
		StatusCode:      txn.StatusCode,
		AmountPaise:     int(txn.Amount),
		RetryCountSoFar: txn.RetryCountSoFar,
	}
	if txn.BankResponseCode != nil {
		payload.BankResponseCode = *txn.BankResponseCode
	}
	if txn.NPCIResponseCode != nil {
		payload.NPCIResponseCode = *txn.NPCIResponseCode
	}
	if txn.CustomerBank != nil {
		payload.IssuerBank = *txn.CustomerBank
	}

	reqBody, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal transaction for ML service: %v", err)
	}

	resp, err := httpClient.Post(endpoint, "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		return nil, fmt.Errorf("failed to call ML service: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ML service returned status code %d", resp.StatusCode)
	}

	var mlResult struct {
		TransactionID     string  `json:"transaction_id"`
		Layer             int     `json:"layer"`
		Cause             string  `json:"cause"`
		Confidence        float64 `json:"confidence"`
		Reasoning         string  `json:"reasoning"`
		RecommendedAction string  `json:"recommended_action"`
		ModelVersion      string  `json:"model_version"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&mlResult); err != nil {
		return nil, fmt.Errorf("failed to decode ML service response: %v", err)
	}

	return &models.ClassificationResult{
		TransactionID:     mlResult.TransactionID,
		Layer:             mlResult.Layer,
		Cause:             mlResult.Cause,
		Confidence:        mlResult.Confidence,
		Reasoning:         mlResult.Reasoning,
		RecommendedAction: mlResult.RecommendedAction,
		ModelVersion:      &mlResult.ModelVersion,
	}, nil
}
