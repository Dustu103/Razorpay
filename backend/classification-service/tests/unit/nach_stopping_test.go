package unit

import (
	"testing"

	"razorpay-classification-service/internal/models"
	"razorpay-classification-service/internal/nach"
)

func TestNACH_Layer0_SIP_Escalations(t *testing.T) {
	// 1 failure -> no stop
	res1 := nach.Check(&models.Transaction{
		ID:                      "txn-sip-1",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeSIP,
		ConsecutiveFailureCount: 1,
	})
	if res1.ShouldStop {
		t.Errorf("Expected SIP failure 1 to pass through Layer 0, got stop")
	}

	// 2 failures -> pre-emptive escalation (before AMC cancellation at 3)
	res2 := nach.Check(&models.Transaction{
		ID:                      "txn-sip-2",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeSIP,
		ConsecutiveFailureCount: 2,
	})
	if !res2.ShouldStop || res2.Result.RecommendedAction != models.ActionSIPCancellationRiskEscalate {
		t.Errorf("Expected pre-emptive escalate for SIP failure 2, got action: %v", res2.Result)
	}

	// 3 failures -> hard stop
	res3 := nach.Check(&models.Transaction{
		ID:                      "txn-sip-3",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeSIP,
		ConsecutiveFailureCount: 3,
	})
	if !res3.ShouldStop || res3.Result.Confidence != 1.0 {
		t.Errorf("Expected hard stop with confidence 1.0 for SIP failure 3, got: %v", res3.Result)
	}
}

func TestNACH_Layer0_EMI_CreditRisk(t *testing.T) {
	days25 := 25
	days28 := 28

	// Under 28 days -> pass through
	res1 := nach.Check(&models.Transaction{
		ID:               "txn-emi-25",
		PaymentRail:      models.PaymentRailNACH,
		ProductType:      models.ProductTypeLoanEMI,
		DaysSinceDueDate: &days25,
	})
	if res1.ShouldStop {
		t.Errorf("Expected EMI at 25 days to pass through, got stop")
	}

	// 28 days -> escalate before 30-day credit bureau reporting
	res2 := nach.Check(&models.Transaction{
		ID:               "txn-emi-28",
		PaymentRail:      models.PaymentRailNACH,
		ProductType:      models.ProductTypeLoanEMI,
		DaysSinceDueDate: &days28,
	})
	if !res2.ShouldStop || res2.Result.RecommendedAction != models.ActionCreditScoreRiskEscalate {
		t.Errorf("Expected credit score risk escalate for EMI at 28 days, got: %v", res2.Result)
	}
}

func TestNACH_Layer0_Insurance_PolicyLapse(t *testing.T) {
	// Insurance failure 1 -> immediate escalation
	res := nach.Check(&models.Transaction{
		ID:                      "txn-ins-1",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeInsurancePremium,
		ConsecutiveFailureCount: 1,
	})
	if !res.ShouldStop || res.Result.RecommendedAction != models.ActionPolicyLapseRiskEscalate {
		t.Errorf("Expected policy lapse risk escalate for insurance failure 1, got: %v", res.Result)
	}
}
