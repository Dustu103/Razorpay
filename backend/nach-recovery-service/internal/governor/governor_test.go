package governor

import (
	"testing"

	"razorpay-nach-recovery-service/internal/models"
)

func intPtr(i int) *int { return &i }

func TestEvaluate_NonNACH(t *testing.T) {
	req := &models.EvaluationRequest{
		TransactionID:           "txn-upi-1",
		PaymentRail:             models.PaymentRailUPI,
		ProductType:             models.ProductTypeSIP,
		ConsecutiveFailureCount: 5,
	}
	res := Evaluate(req)
	if res.GovernorStopped {
		t.Errorf("Expected GovernorStopped=false for non-NACH rail, got true")
	}
}

func TestEvaluate_SIP(t *testing.T) {
	// 1 failure -> no stop
	req1 := &models.EvaluationRequest{
		TransactionID:           "txn-sip-1",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeSIP,
		ConsecutiveFailureCount: 1,
		Cause:                   models.CauseInsufficientFunds,
	}
	res1 := Evaluate(req1)
	if res1.GovernorStopped {
		t.Errorf("Expected SIP 1 failure to not stop")
	}

	// 2 failures -> pre-emptive escalate
	req2 := &models.EvaluationRequest{
		TransactionID:           "txn-sip-2",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeSIP,
		ConsecutiveFailureCount: 2,
		Cause:                   models.CauseInsufficientFunds,
	}
	res2 := Evaluate(req2)
	if !res2.GovernorStopped || res2.Action != models.ActionSIPCancellationRiskEscalate || res2.RecommendedChannel != "sms" {
		t.Errorf("Expected SIP 2 failure to escalate pre-emptively to SMS, got %+v", res2)
	}

	// 3 failures -> hard stop
	req3 := &models.EvaluationRequest{
		TransactionID:           "txn-sip-3",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeSIP,
		ConsecutiveFailureCount: 3,
		Cause:                   models.CauseInsufficientFunds,
	}
	res3 := Evaluate(req3)
	if !res3.GovernorStopped || res3.Confidence != 1.0 {
		t.Errorf("Expected SIP 3 failure hard stop with confidence 1.0, got %+v", res3)
	}
}

func TestEvaluate_LoanEMI(t *testing.T) {
	// Under 28 days -> soft retry
	req1 := &models.EvaluationRequest{
		TransactionID:           "txn-emi-1",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeLoanEMI,
		ConsecutiveFailureCount: 1,
		DaysSinceDueDate:        intPtr(20),
		Cause:                   models.CauseInsufficientFunds,
	}
	res1 := Evaluate(req1)
	if res1.GovernorStopped {
		t.Errorf("Expected EMI at 20 days to not be stopped by Governor")
	}

	// Day 28 -> Credit Risk Escalate to WhatsApp
	req2 := &models.EvaluationRequest{
		TransactionID:           "txn-emi-2",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeLoanEMI,
		ConsecutiveFailureCount: 1,
		DaysSinceDueDate:        intPtr(28),
		Cause:                   models.CauseInsufficientFunds,
	}
	res2 := Evaluate(req2)
	if !res2.GovernorStopped || res2.Action != models.ActionCreditScoreRiskEscalate || res2.RecommendedChannel != "whatsapp" {
		t.Errorf("Expected EMI at 28 days to escalate to WhatsApp, got %+v", res2)
	}
}

func TestEvaluate_Insurance(t *testing.T) {
	req := &models.EvaluationRequest{
		TransactionID:           "txn-ins-1",
		PaymentRail:             models.PaymentRailNACH,
		ProductType:             models.ProductTypeInsurancePremium,
		ConsecutiveFailureCount: 1,
		Cause:                   models.CauseInsufficientFunds,
	}
	res := Evaluate(req)
	if !res.GovernorStopped || res.Action != models.ActionPolicyLapseRiskEscalate || res.RecommendedChannel != "sms" {
		t.Errorf("Expected Insurance at 1 failure to escalate to SMS, got %+v", res)
	}
}

func TestEvaluate_PermanentCauses(t *testing.T) {
	hardCauses := []string{
		models.CauseMandateExpired,
		models.CauseAccountFrozenOrClosed,
		models.CauseIncorrectMandateDetails,
	}

	for _, cause := range hardCauses {
		req := &models.EvaluationRequest{
			TransactionID:           "txn-hard",
			PaymentRail:             models.PaymentRailNACH,
			ProductType:             models.ProductTypeSIP,
			ConsecutiveFailureCount: 1,
			Cause:                   cause,
		}
		res := Evaluate(req)
		if !res.GovernorStopped || res.Action != models.ActionNACHDoNotRetry {
			t.Errorf("Expected %s to result in nach_do_not_retry, got %+v", cause, res)
		}
	}
}
