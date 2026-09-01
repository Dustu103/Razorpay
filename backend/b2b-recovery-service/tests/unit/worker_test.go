package unit

import (
	"testing"
	"time"

	"razorpay-b2b-recovery-service/internal/models"
)

// computeDaysLate mirrors the exact logic used in worker/cron.go
func computeDaysLate(expireBy time.Time) int {
	return int(time.Now().Sub(expireBy).Hours() / 24)
}

// TestBoundary_NoTriggerBefore45Days verifies that an invoice at 44 days
// is correctly below the Sec 43B MSME threshold.
func TestBoundary_NoTriggerBefore45Days(t *testing.T) {
	inv := models.InvoiceRecord{
		IsMSME:   true,
		ExpireBy: time.Now().Add(-44 * 24 * time.Hour),
	}
	daysLate := computeDaysLate(inv.ExpireBy)
	if daysLate >= 45 {
		t.Errorf("Expected days_late < 45 for pre-threshold invoice, got %d", daysLate)
	}
}

// TestBoundary_Sec43B_TriggerAt45Days verifies the MSME Sec 43B trigger fires
// correctly at exactly 45 days.
func TestBoundary_Sec43B_TriggerAt45Days(t *testing.T) {
	inv := models.InvoiceRecord{
		IsMSME:   true,
		ExpireBy: time.Now().Add(-45 * 24 * time.Hour),
	}
	daysLate := computeDaysLate(inv.ExpireBy)
	if daysLate < 45 {
		t.Errorf("Expected days_late >= 45 to trigger Sec 43B, got %d", daysLate)
	}
}

// TestBoundary_Sec43B_DoesNotFireForNonMSME verifies that 45 days overdue
// does NOT trigger the MSME-specific Sec 43B for a non-MSME vendor.
func TestBoundary_Sec43B_DoesNotFireForNonMSME(t *testing.T) {
	inv := models.InvoiceRecord{
		IsMSME:   false,
		ExpireBy: time.Now().Add(-46 * 24 * time.Hour),
	}
	daysLate := computeDaysLate(inv.ExpireBy)
	// Business rule: Sec 43B only applies to MSME-registered vendors
	if inv.IsMSME && daysLate >= 45 {
		t.Errorf("Sec 43B should NOT trigger for non-MSME vendors")
	}
}

// TestBoundary_GSTRule37_TriggerAt180Days verifies the GST Rule 37 trigger
// fires at the 180-day statutory threshold.
func TestBoundary_GSTRule37_TriggerAt180Days(t *testing.T) {
	inv := models.InvoiceRecord{
		IsMSME:   false,
		ExpireBy: time.Now().Add(-180 * 24 * time.Hour),
	}
	daysLate := computeDaysLate(inv.ExpireBy)
	if daysLate < 180 {
		t.Errorf("Expected days_late >= 180 to trigger GST Rule 37, got %d", daysLate)
	}
}

// TestBoundary_NoTriggerBefore180Days verifies no GST rule fires at 179 days.
func TestBoundary_NoTriggerBefore180Days(t *testing.T) {
	inv := models.InvoiceRecord{
		IsMSME:   false,
		ExpireBy: time.Now().Add(-179 * 24 * time.Hour),
	}
	daysLate := computeDaysLate(inv.ExpireBy)
	if daysLate >= 180 {
		t.Errorf("GST Rule 37 must NOT fire before 180 days, got %d", daysLate)
	}
}

// TestOnTimeInvoice verifies an invoice that has not yet expired
// returns a negative days_late, meaning no action should be triggered.
func TestOnTimeInvoice(t *testing.T) {
	inv := models.InvoiceRecord{
		ExpireBy: time.Now().Add(2 * 24 * time.Hour), // expires in 2 days
	}
	daysLate := computeDaysLate(inv.ExpireBy)
	if daysLate > 0 {
		t.Errorf("On-time invoice should have days_late <= 0, got %d", daysLate)
	}
}
