package models

import "time"

// InvoiceRecord represents an unpaid invoice from the database
type InvoiceRecord struct {
	ID        string
	Customer  string
	Amount    float64
	IsMSME    bool
	ExpireBy  time.Time
}

// AgentRequest is the payload sent to the Python inference-service
type AgentRequest struct {
	ID               string  `json:"id"`
	CustomerName     string  `json:"customer_name"`
	AmountDue        float64 `json:"amount_due"`
	IsMSMERegistered bool    `json:"is_msme_registered"`
	DaysLate         int     `json:"days_late"`
}

// AgentResponse is the payload received from the Python inference-service
type AgentResponse struct {
	Action           string `json:"action"`
	TaxRuleTriggered string `json:"tax_rule_triggered"`
	DraftEmailBody   string `json:"draft_email_body"`
}
