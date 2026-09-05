package models

import (
	"time"
)

// WebhookPayload is what Razorpay POSTs to our ingestion endpoint.
// Only the fields we need for classification are captured here.
type WebhookPayload struct {
	Event   string          `json:"event"`
	Payload PaymentPayload  `json:"payload"`
}

type PaymentPayload struct {
	Payment PaymentEntity `json:"payment"`
}

type PaymentEntity struct {
	Entity PaymentData `json:"entity"`
}

type PaymentData struct {
	ID                        string   `json:"id"`   // gateway_transaction_id
	StatusCode                string   `json:"status_code"`
	NPCIResponseCode          *string  `json:"npci_txn_id"`  // may be absent
	BankResponseCode          *string  `json:"acquirer_data"`
	Amount                    float64  `json:"amount"`
	Bank                      *string  `json:"bank"`
	RetryCount                int      `json:"retry_count"`
	MandateNotificationSentAt *string  `json:"mandate_notification_sent_at"` // RFC3339 or null
	DebitScheduledAt          *string  `json:"debit_scheduled_at"`           // RFC3339 or null
	PaymentRail               *string  `json:"payment_rail,omitempty"`       // "nach" | "upi" | "card"
	ProductType               *string  `json:"product_type,omitempty"`       // "sip" | "loan_emi" | "insurance_premium"
	ConsecutiveFailureCount   *int     `json:"consecutive_failure_count,omitempty"`
	DaysSinceDueDate          *int     `json:"days_since_due_date,omitempty"`
}

// Transaction is the normalised row written to the DB.
type Transaction struct {
	ID                         string     `json:"id"`
	GatewayTransactionID       string     `json:"gateway_transaction_id"`
	StatusCode                 string     `json:"status_code"`
	NPCIResponseCode           *string    `json:"npci_response_code"`
	BankResponseCode           *string    `json:"bank_response_code"`
	Amount                     float64    `json:"amount"`
	CustomerBank               *string    `json:"customer_bank"`
	RetryCountSoFar            int        `json:"retry_count_so_far"`
	MandateNotificationSentAt  *time.Time `json:"mandate_notification_sent_at"`
	DebitScheduledAt           *time.Time `json:"debit_scheduled_at"`
	PaymentRail                *string    `json:"payment_rail,omitempty"`
	ProductType                *string    `json:"product_type,omitempty"`
	ConsecutiveFailureCount    *int       `json:"consecutive_failure_count,omitempty"`
	DaysSinceDueDate           *int       `json:"days_since_due_date,omitempty"`
	CreatedAt                  time.Time  `json:"created_at"`
}

// ClassificationJob is the envelope queued to Redis for the classification worker.
type ClassificationJob struct {
	TransactionID string `json:"transaction_id"`
}

// ErrorResponse is the standard error JSON shape across services.
type ErrorResponse struct {
	Error string `json:"error"`
	Code  string `json:"code,omitempty"`
}
