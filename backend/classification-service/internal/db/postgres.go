package db

import (
	"context"
	"fmt"
	"os"

	"razorpay-classification-service/internal/models"

	"github.com/jackc/pgx/v5"
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

// GetTransaction fetches a transaction row by UUID.
func (d *DB) GetTransaction(ctx context.Context, id string) (*models.Transaction, error) {
	query := `
		SELECT id, gateway_transaction_id, status_code,
		       npci_response_code, bank_response_code,
		       amount, customer_bank, retry_count_so_far,
		       mandate_notification_sent_at, debit_scheduled_at
		FROM transactions WHERE id = $1`

	var txn models.Transaction
	err := d.pool.QueryRow(ctx, query, id).Scan(
		&txn.ID,
		&txn.GatewayTransactionID,
		&txn.StatusCode,
		&txn.NPCIResponseCode,
		&txn.BankResponseCode,
		&txn.Amount,
		&txn.CustomerBank,
		&txn.RetryCountSoFar,
		&txn.MandateNotificationSentAt,
		&txn.DebitScheduledAt,
	)
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("transaction %s not found", id)
		}
		return nil, fmt.Errorf("get transaction: %w", err)
	}
	return &txn, nil
}

// SaveClassification writes the classification result to the DB.
func (d *DB) SaveClassification(ctx context.Context, r *models.ClassificationResult) error {
	query := `
		INSERT INTO classifications (
			transaction_id, layer, cause, confidence,
			reasoning, recommended_action, model_version
		) VALUES ($1, $2, $3, $4, $5, $6, $7)`

	_, err := d.pool.Exec(ctx, query,
		r.TransactionID,
		r.Layer,
		r.Cause,
		r.Confidence,
		r.Reasoning,
		r.RecommendedAction,
		r.ModelVersion,
	)
	if err != nil {
		return fmt.Errorf("save classification: %w", err)
	}
	return nil
}
