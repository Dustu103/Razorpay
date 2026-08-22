package models

import "time"

// ClassificationView is the joined read model returned by the audit API.
type ClassificationView struct {
	ID                   string     `json:"id"`
	TransactionID        string     `json:"transaction_id"`
	GatewayTransactionID string     `json:"gateway_transaction_id"`
	Layer                int        `json:"layer"`
	Cause                string     `json:"cause"`
	Confidence           float64    `json:"confidence"`
	Reasoning            string     `json:"reasoning"`
	RecommendedAction    string     `json:"recommended_action"`
	ModelVersion         *string    `json:"model_version"`
	StatusCode           string     `json:"status_code"`
	NPCIResponseCode     *string    `json:"npci_response_code"`
	BankResponseCode     *string    `json:"bank_response_code"`
	Amount               float64    `json:"amount"`
	CustomerBank         *string    `json:"customer_bank"`
	RetryCountSoFar      int        `json:"retry_count_so_far"`
	CreatedAt            time.Time  `json:"created_at"`
}

// ListFilter is parsed from query params.
type ListFilter struct {
	Cause string
	Layer *int
	Limit  int
	Offset int
}

// ErrorResponse is the standard error envelope.
type ErrorResponse struct {
	Error string `json:"error"`
	Code  string `json:"code,omitempty"`
}
