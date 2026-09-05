-- Migration 003: Add NACH mandate recovery fields to transactions table.
--
-- These columns are nullable so existing UPI/card rows are unaffected.
-- The classification service uses COALESCE('') on payment_rail and product_type,
-- and COALESCE(0) on consecutive_failure_count, so the Go layer never sees NULL
-- for these fields.
--
-- Applied: 2026-09-05

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS payment_rail             TEXT    DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS product_type             TEXT    DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS consecutive_failure_count INTEGER DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS days_since_due_date      INTEGER DEFAULT NULL;

-- Partial index for fast NACH-rail queries (stopping policy check is on NACH only).
CREATE INDEX IF NOT EXISTS idx_transactions_nach_rail
    ON transactions (payment_rail, product_type, consecutive_failure_count)
    WHERE payment_rail = 'nach';

COMMENT ON COLUMN transactions.payment_rail IS
    'Payment rail: nach | upi | card. NULL for legacy rows.';
COMMENT ON COLUMN transactions.product_type IS
    'NACH product type: sip | loan_emi | insurance_premium. NULL for non-NACH rows.';
COMMENT ON COLUMN transactions.consecutive_failure_count IS
    'Number of consecutive mandate debit failures on this mandate ID. NULL for non-NACH rows.';
COMMENT ON COLUMN transactions.days_since_due_date IS
    'Days elapsed since scheduled due date (EMI only). NULL for SIP/insurance/non-NACH rows.';
