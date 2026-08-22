package db

import (
	"context"
	"fmt"
	"os"

	"razorpay-ingestion-service/internal/models"

	"github.com/jackc/pgx/v5/pgxpool"
)

type DB struct {
	pool *pgxpool.Pool
}

func Connect(ctx context.Context) (*DB, error) {
	url := os.Getenv("DATABASE_URL")
	if url == "" {
		return nil, fmt.Errorf("DATABASE_URL is not set")
	}
	pool, err := pgxpool.New(ctx, url)
	if err != nil {
		return nil, fmt.Errorf("pgxpool.New: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("db ping: %w", err)
	}
	return &DB{pool: pool}, nil
}

func (d *DB) Close() { d.pool.Close() }

// UpsertTransaction performs an atomic dedup upsert.
// Returns the UUID of the (existing or new) transaction row.
// Returns ("", false, nil) when the event was already ingested (duplicate).
func (d *DB) UpsertTransaction(ctx context.Context, t *models.Transaction) (id string, isNew bool, err error) {
	query := `
		INSERT INTO transactions (
			gateway_transaction_id, status_code, npci_response_code,
			bank_response_code, amount, customer_bank, retry_count_so_far,
			mandate_notification_sent_at, debit_scheduled_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		ON CONFLICT (gateway_transaction_id) DO NOTHING
		RETURNING id`

	err = d.pool.QueryRow(ctx, query,
		t.GatewayTransactionID,
		t.StatusCode,
		t.NPCIResponseCode,
		t.BankResponseCode,
		t.Amount,
		t.CustomerBank,
		t.RetryCountSoFar,
		t.MandateNotificationSentAt,
		t.DebitScheduledAt,
	).Scan(&id)

	if err != nil {
		// pgx returns ErrNoRows when ON CONFLICT DO NOTHING fires (no row returned)
		if err.Error() == "no rows in result set" {
			return "", false, nil // duplicate — already ingested
		}
		return "", false, fmt.Errorf("upsert transaction: %w", err)
	}
	return id, true, nil
}
