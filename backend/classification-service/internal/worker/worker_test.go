package worker

import (
	"testing"

	"razorpay-classification-service/internal/models"
)

func TestBuildFallbackResult(t *testing.T) {
	txn := &models.Transaction{
		ID: "txn-fallback",
	}

	res := buildFallbackResult(txn)

	if res.TransactionID != "txn-fallback" {
		t.Errorf("Expected transaction ID to match, got %s", res.TransactionID)
	}
	if res.Layer != 2 {
		t.Errorf("Expected Layer 2 for global fallback, got %d", res.Layer)
	}
	if res.Cause != models.CauseSoftDecline {
		t.Errorf("Expected safe fallback cause to be soft_decline, got %s", res.Cause)
	}
	if res.RecommendedAction != models.ActionRetryScheduled {
		t.Errorf("Expected safe fallback action to be retry_scheduled, got %s", res.RecommendedAction)
	}
	if res.Confidence != 0.0 {
		t.Errorf("Expected 0.0 confidence for global fallback, got %f", res.Confidence)
	}
}

func TestConsequenceSeverity(t *testing.T) {
	tests := []struct {
		name     string
		rail     string
		product  string
		expected string
	}{
		{
			name:     "NACH Loan EMI maps to credit_score_risk",
			rail:     models.PaymentRailNACH,
			product:  models.ProductTypeLoanEMI,
			expected: models.ConsequenceCreditScoreRisk,
		},
		{
			name:     "NACH SIP maps to investment_lapse_risk",
			rail:     models.PaymentRailNACH,
			product:  models.ProductTypeSIP,
			expected: models.ConsequenceInvestmentLapseRisk,
		},
		{
			name:     "NACH Insurance Premium maps to policy_lapse_risk",
			rail:     models.PaymentRailNACH,
			product:  models.ProductTypeInsurancePremium,
			expected: models.ConsequencePolicyLapseRisk,
		},
		{
			name:     "NACH unknown product maps to empty",
			rail:     models.PaymentRailNACH,
			product:  "generic_saas",
			expected: "",
		},
		{
			name:     "Non-NACH rail (UPI) maps to empty even if product is EMI",
			rail:     models.PaymentRailUPI,
			product:  models.ProductTypeLoanEMI,
			expected: "",
		},
		{
			name:     "Non-NACH rail (Card) maps to empty even if product is SIP",
			rail:     models.PaymentRailCard,
			product:  models.ProductTypeSIP,
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			txn := &models.Transaction{
				PaymentRail: tt.rail,
				ProductType: tt.product,
			}
			got := consequenceSeverity(txn)
			if got != tt.expected {
				t.Errorf("consequenceSeverity() = %q, want %q", got, tt.expected)
			}
		})
	}
}
