package nach

import (
	"testing"

	"razorpay-classification-service/internal/models"
)

func intPtr(i int) *int {
	return &i
}

func TestCheck_NonNACHRail(t *testing.T) {
	// UPI and Card transactions must always pass through Layer 0 untouched.
	rails := []string{models.PaymentRailUPI, models.PaymentRailCard, "netbanking", ""}

	for _, rail := range rails {
		txn := &models.Transaction{
			ID:                       "txn-non-nach",
			PaymentRail:              rail,
			ProductType:              models.ProductTypeSIP,
			ConsecutiveFailureCount: 5, // High count, but not NACH rail
			DaysSinceDueDate:         intPtr(35),
		}

		res := Check(txn)
		if res.ShouldStop {
			t.Errorf("Expected ShouldStop=false for non-NACH rail %q, got true", rail)
		}
		if res.Result != nil {
			t.Errorf("Expected nil Result for non-NACH rail %q, got %+v", rail, res.Result)
		}
	}
}

func TestCheck_SIP_UnderThreshold(t *testing.T) {
	// For SIP, consecutive failures < 2 should pass through to normal classifier.
	counts := []int{0, 1}

	for _, count := range counts {
		txn := &models.Transaction{
			ID:                       "txn-sip-ok",
			PaymentRail:              models.PaymentRailNACH,
			ProductType:              models.ProductTypeSIP,
			ConsecutiveFailureCount: count,
		}

		res := Check(txn)
		if res.ShouldStop {
			t.Errorf("Expected ShouldStop=false for SIP with %d failures, got true", count)
		}
	}
}

func TestCheck_SIP_PreEmptiveEscalate(t *testing.T) {
	// AMC cancellation is at 3 failures. We must pre-emptively escalate at 2 failures.
	txn := &models.Transaction{
		ID:                       "txn-sip-escalate",
		PaymentRail:              models.PaymentRailNACH,
		ProductType:              models.ProductTypeSIP,
		ConsecutiveFailureCount: 2,
	}

	res := Check(txn)
	if !res.ShouldStop {
		t.Fatalf("Expected ShouldStop=true for SIP with 2 failures, got false")
	}
	if res.Result == nil {
		t.Fatalf("Expected non-nil Result for SIP with 2 failures")
	}

	r := res.Result
	if r.Layer != 0 {
		t.Errorf("Expected Layer 0, got %d", r.Layer)
	}
	if r.Cause != models.CauseNACHInsufficientFunds {
		t.Errorf("Expected cause %s, got %s", models.CauseNACHInsufficientFunds, r.Cause)
	}
	if r.RecommendedAction != models.ActionSIPCancellationRiskEscalate {
		t.Errorf("Expected action %s, got %s", models.ActionSIPCancellationRiskEscalate, r.RecommendedAction)
	}
	if r.Confidence != 0.95 {
		t.Errorf("Expected confidence 0.95, got %f", r.Confidence)
	}
	if r.ModelVersion == nil || *r.ModelVersion != "nach-stopping-sip-pre-emptive-escalate" {
		t.Errorf("Expected model version nach-stopping-sip-pre-emptive-escalate, got %v", r.ModelVersion)
	}
}

func TestCheck_SIP_HardStop(t *testing.T) {
	// At >= 3 failures, AMC cancellation threshold is reached. Retry is futile.
	for _, count := range []int{3, 4, 10} {
		txn := &models.Transaction{
			ID:                       "txn-sip-hard-stop",
			PaymentRail:              models.PaymentRailNACH,
			ProductType:              models.ProductTypeSIP,
			ConsecutiveFailureCount: count,
		}

		res := Check(txn)
		if !res.ShouldStop {
			t.Fatalf("Expected ShouldStop=true for SIP with %d failures, got false", count)
		}
		r := res.Result
		if r.Layer != 0 {
			t.Errorf("Expected Layer 0, got %d", r.Layer)
		}
		if r.Confidence != 1.0 {
			t.Errorf("Expected confidence 1.0 for hard stop, got %f", r.Confidence)
		}
		if r.RecommendedAction != models.ActionSIPCancellationRiskEscalate {
			t.Errorf("Expected action %s, got %s", models.ActionSIPCancellationRiskEscalate, r.RecommendedAction)
		}
		if r.ModelVersion == nil || *r.ModelVersion != "nach-stopping-sip-hard-stop" {
			t.Errorf("Expected model version nach-stopping-sip-hard-stop, got %v", r.ModelVersion)
		}
	}
}

func TestCheck_LoanEMI_NoDueDate(t *testing.T) {
	// If due date is missing (nil), fall through to normal classification.
	txn := &models.Transaction{
		ID:               "txn-emi-no-due-date",
		PaymentRail:      models.PaymentRailNACH,
		ProductType:      models.ProductTypeLoanEMI,
		DaysSinceDueDate: nil,
	}

	res := Check(txn)
	if res.ShouldStop {
		t.Errorf("Expected ShouldStop=false for EMI with nil DaysSinceDueDate, got true")
	}
}

func TestCheck_LoanEMI_Under28Days(t *testing.T) {
	// Credit bureau reporting happens at 30 days. Under 28 days, retry may be viable.
	for _, days := range []int{0, 7, 14, 27} {
		txn := &models.Transaction{
			ID:               "txn-emi-ok",
			PaymentRail:      models.PaymentRailNACH,
			ProductType:      models.ProductTypeLoanEMI,
			DaysSinceDueDate: intPtr(days),
		}

		res := Check(txn)
		if res.ShouldStop {
			t.Errorf("Expected ShouldStop=false for EMI at %d days since due date, got true", days)
		}
	}
}

func TestCheck_LoanEMI_AtOrOver28Days(t *testing.T) {
	// At >= 28 days, escalate directly to human contact before credit bureau reporting.
	for _, days := range []int{28, 29, 30, 45} {
		txn := &models.Transaction{
			ID:               "txn-emi-escalate",
			PaymentRail:      models.PaymentRailNACH,
			ProductType:      models.ProductTypeLoanEMI,
			DaysSinceDueDate: intPtr(days),
		}

		res := Check(txn)
		if !res.ShouldStop {
			t.Fatalf("Expected ShouldStop=true for EMI at %d days, got false", days)
		}
		r := res.Result
		if r.Layer != 0 {
			t.Errorf("Expected Layer 0, got %d", r.Layer)
		}
		if r.Confidence != 1.0 {
			t.Errorf("Expected confidence 1.0, got %f", r.Confidence)
		}
		if r.RecommendedAction != models.ActionCreditScoreRiskEscalate {
			t.Errorf("Expected action %s, got %s", models.ActionCreditScoreRiskEscalate, r.RecommendedAction)
		}
		if r.ModelVersion == nil || *r.ModelVersion != "nach-stopping-emi-credit-risk-escalate" {
			t.Errorf("Expected model version nach-stopping-emi-credit-risk-escalate, got %v", r.ModelVersion)
		}
	}
}

func TestCheck_Insurance_NoFailures(t *testing.T) {
	// 0 failures -> no stop
	txn := &models.Transaction{
		ID:                       "txn-ins-0",
		PaymentRail:              models.PaymentRailNACH,
		ProductType:              models.ProductTypeInsurancePremium,
		ConsecutiveFailureCount: 0,
	}

	res := Check(txn)
	if res.ShouldStop {
		t.Errorf("Expected ShouldStop=false for Insurance with 0 failures, got true")
	}
}

func TestCheck_Insurance_OneOrMoreFailures(t *testing.T) {
	// Insurance coverage terminates quickly; single failure requires immediate escalation.
	for _, count := range []int{1, 2, 5} {
		txn := &models.Transaction{
			ID:                       "txn-ins-escalate",
			PaymentRail:              models.PaymentRailNACH,
			ProductType:              models.ProductTypeInsurancePremium,
			ConsecutiveFailureCount: count,
		}

		res := Check(txn)
		if !res.ShouldStop {
			t.Fatalf("Expected ShouldStop=true for Insurance with %d failure(s), got false", count)
		}
		r := res.Result
		if r.Layer != 0 {
			t.Errorf("Expected Layer 0, got %d", r.Layer)
		}
		if r.Confidence != 0.90 {
			t.Errorf("Expected confidence 0.90, got %f", r.Confidence)
		}
		if r.RecommendedAction != models.ActionPolicyLapseRiskEscalate {
			t.Errorf("Expected action %s, got %s", models.ActionPolicyLapseRiskEscalate, r.RecommendedAction)
		}
		if r.ModelVersion == nil || *r.ModelVersion != "nach-stopping-insurance-lapse-escalate" {
			t.Errorf("Expected model version nach-stopping-insurance-lapse-escalate, got %v", r.ModelVersion)
		}
	}
}

func TestCheck_UnknownProduct(t *testing.T) {
	// Unknown product types on NACH rail should fall through safely.
	txn := &models.Transaction{
		ID:                       "txn-unknown-prod",
		PaymentRail:              models.PaymentRailNACH,
		ProductType:              "general_subscription",
		ConsecutiveFailureCount: 5,
		DaysSinceDueDate:         intPtr(40),
	}

	res := Check(txn)
	if res.ShouldStop {
		t.Errorf("Expected ShouldStop=false for unknown product type, got true")
	}
}
