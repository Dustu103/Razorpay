package layer2

import (
	"bytes"
	"context"
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
func Classify(ctx context.Context, txn *models.Transaction) (*models.ClassificationResult, error) {
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

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewBuffer(reqBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request for ML service: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := httpClient.Do(req)
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

// CheckFalseDecline calls the ML service to check if a fraud filter block is a false decline.
func CheckFalseDecline(txn *models.Transaction) (float64, string, error) {
	mlURL := os.Getenv("ML_SERVICE_URL")
	if mlURL == "" {
		mlURL = "http://localhost:8000"
	}
	endpoint := fmt.Sprintf("%s/predict/false-decline", mlURL)

	payload := map[string]interface{}{
		"amount":               txn.Amount,
		"transaction_velocity": 1, // simplified for now
		"is_known_device":      1,
		"ip_risk_score":        0.1,
		"merchant_category":    "retail",
		"transaction_hour":     12,
	}

	reqBody, _ := json.Marshal(payload)
	resp, err := httpClient.Post(endpoint, "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		return 0, "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, "", fmt.Errorf("ML service returned %d", resp.StatusCode)
	}

	var res struct {
		Likelihood float64 `json:"false_decline_likelihood"`
		Action     string  `json:"recommended_action"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return 0, "", err
	}

	return res.Likelihood, res.Action, nil
}

// EvaluateRetry calls the ML service to get the probability of a successful retry.
func EvaluateRetry(txn *models.Transaction) (float64, string, error) {
	mlURL := os.Getenv("ML_SERVICE_URL")
	if mlURL == "" {
		mlURL = "http://localhost:8000"
	}
	endpoint := fmt.Sprintf("%s/predict/retry", mlURL)

	payload := map[string]interface{}{
		"hour_of_day":             12,
		"day_of_month":            15,
		"failure_cause_encoded":   0,
		"payment_method_encoded":  1,
		"retry_count":             txn.RetryCountSoFar,
		"time_since_failure_mins": 30,
	}

	reqBody, _ := json.Marshal(payload)
	resp, err := httpClient.Post(endpoint, "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		return 0, "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, "", fmt.Errorf("ML service returned %d", resp.StatusCode)
	}

	var res struct {
		Probability float64 `json:"retry_success_probability"`
		Action      string  `json:"recommended_action"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return 0, "", err
	}

	return res.Probability, res.Action, nil
}

// EvaluateDunning calls the ML service to get the best dunning channel.
func EvaluateDunning(txn *models.Transaction) (float64, string, error) {
	mlURL := os.Getenv("ML_SERVICE_URL")
	if mlURL == "" {
		mlURL = "http://localhost:8000"
	}
	endpoint := fmt.Sprintf("%s/predict/dunning", mlURL)

	payload := map[string]interface{}{
		"channel_encoded":            0, // start with email
		"time_since_failure_mins":    60,
		"customer_tenure_months":     12,
		"prior_payment_success_rate": 0.8,
	}

	reqBody, _ := json.Marshal(payload)
	resp, err := httpClient.Post(endpoint, "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		return 0, "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, "", fmt.Errorf("ML service returned %d", resp.StatusCode)
	}

	var res struct {
		Probability float64 `json:"payment_probability"`
		Channel     string  `json:"recommended_channel"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return 0, "", err
	}

	return res.Probability, res.Channel, nil
}

// CheckRBICompliance calls the compliance service to enforce the 8 AM to 7 PM IST limit and max 3 contacts.
func CheckRBICompliance(borrowerID string) (bool, string, error) {
	complianceURL := os.Getenv("COMPLIANCE_SERVICE_URL")
	if complianceURL == "" {
		complianceURL = "http://localhost:3004"
	}
	endpoint := fmt.Sprintf("%s/api/v1/compliance/rbi-dunning-window?borrower_id=%s", complianceURL, borrowerID)

	resp, err := httpClient.Get(endpoint)
	if err != nil {
		return false, "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return false, "", fmt.Errorf("compliance service returned %d", resp.StatusCode)
	}

	var res struct {
		Allowed       bool   `json:"allowed"`
		Reason        string `json:"reason"`
		IstTime       string `json:"ist_time"`
		AttemptsToday int    `json:"attempts_today"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return false, "", err
	}

	return res.Allowed, res.Reason, nil
}

// EvaluateBNPLRecovery calls the ML service to determine the best recovery channel based on ecosystem debt.
func EvaluateBNPLRecovery(borrowerID string, internalDebt, externalDebt float64, daysSinceLogin, demographicAge int, consentRevoked bool, externalDebtDataAgeDays int) (string, error) {
	mlURL := os.Getenv("ML_SERVICE_URL")
	if mlURL == "" {
		mlURL = "http://localhost:8000"
	}
	endpoint := fmt.Sprintf("%s/predict/bnpl-recovery", mlURL)

	payload := map[string]interface{}{
		"internal_debt":               internalDebt,
		"external_ecosystem_debt":     externalDebt,
		"days_since_login":            daysSinceLogin,
		"demographic_age":             demographicAge,
		"consent_revoked":             consentRevoked,
		"external_debt_data_age_days": externalDebtDataAgeDays,
	}

	reqBody, _ := json.Marshal(payload)
	resp, err := httpClient.Post(endpoint, "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("ML service returned %d", resp.StatusCode)
	}

	var res struct {
		RecommendedChannel string `json:"recommended_channel"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return "", err
	}

	return res.RecommendedChannel, nil
}

