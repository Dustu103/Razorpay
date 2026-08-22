-- Feature 1: Root-Cause Classifier Schema
-- Run this once against your Postgres instance before starting any service.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────────────────────
-- transactions: raw webhook payloads, deduplicated by gateway_transaction_id
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    gateway_transaction_id      TEXT        NOT NULL UNIQUE,    -- dedup key (at-least-once delivery)
    status_code                 TEXT        NOT NULL,
    npci_response_code          TEXT,
    bank_response_code          TEXT,
    amount                      NUMERIC     NOT NULL,
    customer_bank               TEXT,
    retry_count_so_far          INT         NOT NULL DEFAULT 0,
    mandate_notification_sent_at TIMESTAMPTZ,
    debit_scheduled_at          TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_gateway_id
    ON transactions (gateway_transaction_id);

-- ─────────────────────────────────────────────────────────────
-- classifications: one row per transaction, written after Layer 1 or 2 runs
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS classifications (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id      UUID        NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    layer               SMALLINT    NOT NULL CHECK (layer IN (1, 2)),
    cause               TEXT        NOT NULL,           -- e.g. soft_decline, notification_compliance_block
    confidence          NUMERIC(4,3) NOT NULL,          -- 0.000 – 1.000
    reasoning           TEXT        NOT NULL,
    recommended_action  TEXT        NOT NULL,           -- retry_now | retry_scheduled | do_not_retry | ...
    model_version       TEXT,                           -- NULL for Layer 1 (deterministic)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_classifications_transaction_id
    ON classifications (transaction_id);

CREATE INDEX IF NOT EXISTS idx_classifications_cause
    ON classifications (cause);
