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
	Timeout: 15 * time.Second,
}

// hardDeclineCodes are response codes that are definitionally unretryable.
// These are intercepted BEFORE the ML call to prevent miscalibration errors.
// Reference: RBI / NPCI / ISO 8583 error code taxonomy.
var hardDeclineNPCI = map[string]string{
	"U002": "Bank not registered on UPI — permanent hard decline.",
	"U030": "Transaction declined by issuer bank — permanent hard decline.",
	"U028": "Party not enabled for UPI — permanent hard decline.",
}

var hardDeclineBank = map[string]string{
	"54": "Expired card — permanent hard decline, do not retry.",
	"41": "Lost card — permanent fraud signal, do not retry.",
	"43": "Stolen card — permanent fraud signal, do not retry.",
	"62": "Restricted card — permanent compliance block, do not retry.",
}

// Classify makes an HTTP POST request to the Python ml-service.
func Classify(txn *models.Transaction) (*models.ClassificationResult, error) {
	// ── Pre-ML Deterministic Intercept ─────────────────────────────────────
	// Check for codes that are definitionally unambiguous hard declines.
	// The ML model can miscalibrate on rare codes — we never retry these.
	if txn.NPCIResponseCode != nil {
		if reason, ok := hardDeclineNPCI[*txn.NPCIResponseCode]; ok {
			mv := "layer2-deterministic-npci-blocklist"
			return &models.ClassificationResult{
				TransactionID:     txn.ID,
				Layer:             2,
				Cause:             models.CauseHardDecline,
				Confidence:        1.0,
				Reasoning:         reason,
				RecommendedAction: models.ActionDoNotRetry,
				ModelVersion:      &mv,
			}, nil
		}
	}
	if txn.BankResponseCode != nil {
		if reason, ok := hardDeclineBank[*txn.BankResponseCode]; ok {
			mv := "layer2-deterministic-bank-blocklist"
			return &models.ClassificationResult{
				TransactionID:     txn.ID,
				Layer:             2,
				Cause:             models.CauseHardDecline,
				Confidence:        1.0,
				Reasoning:         reason,
				RecommendedAction: models.ActionDoNotRetry,
				ModelVersion:      &mv,
			}, nil
		}
	}
	mlURL := os.Getenv("ML_SERVICE_URL")
	if mlURL == "" {
		mlURL = "http://localhost:8000"
	}
	
	endpoint := fmt.Sprintf("%s/predict/payment", mlURL)

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
