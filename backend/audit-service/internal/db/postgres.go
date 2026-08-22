package db

import (
	"context"
	"fmt"
	"os"

	"razorpay-audit-service/internal/models"

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

// ListClassifications returns a joined view of classifications + transactions.
// Supports filtering by cause and/or layer, with pagination.
func (d *DB) ListClassifications(ctx context.Context, f models.ListFilter) ([]models.ClassificationView, error) {
	query := `
		SELECT
			c.id, c.transaction_id, t.gateway_transaction_id,
			c.layer, c.cause, c.confidence, c.reasoning,
			c.recommended_action, c.model_version,
			t.status_code, t.npci_response_code, t.bank_response_code,
			t.amount, t.customer_bank, t.retry_count_so_far,
			c.created_at
		FROM classifications c
		JOIN transactions t ON t.id = c.transaction_id
		WHERE ($1 = '' OR c.cause = $1)
		  AND ($2 = 0  OR c.layer = $2)
		ORDER BY c.created_at DESC
		LIMIT $3 OFFSET $4`

	layer := 0
	if f.Layer != nil {
		layer = *f.Layer
	}
	limit := f.Limit
	if limit <= 0 || limit > 100 {
		limit = 50
	}

	rows, err := d.pool.Query(ctx, query, f.Cause, layer, limit, f.Offset)
	if err != nil {
		return nil, fmt.Errorf("list classifications: %w", err)
	}
	defer rows.Close()

	var results []models.ClassificationView
	for rows.Next() {
		var v models.ClassificationView
		if err := rows.Scan(
			&v.ID, &v.TransactionID, &v.GatewayTransactionID,
			&v.Layer, &v.Cause, &v.Confidence, &v.Reasoning,
			&v.RecommendedAction, &v.ModelVersion,
			&v.StatusCode, &v.NPCIResponseCode, &v.BankResponseCode,
			&v.Amount, &v.CustomerBank, &v.RetryCountSoFar,
			&v.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		results = append(results, v)
	}
	return results, nil
}

// GetClassification returns a single classification by UUID.
func (d *DB) GetClassification(ctx context.Context, id string) (*models.ClassificationView, error) {
	query := `
		SELECT
			c.id, c.transaction_id, t.gateway_transaction_id,
			c.layer, c.cause, c.confidence, c.reasoning,
			c.recommended_action, c.model_version,
			t.status_code, t.npci_response_code, t.bank_response_code,
			t.amount, t.customer_bank, t.retry_count_so_far,
			c.created_at
		FROM classifications c
		JOIN transactions t ON t.id = c.transaction_id
		WHERE c.id = $1`

	var v models.ClassificationView
	err := d.pool.QueryRow(ctx, query, id).Scan(
		&v.ID, &v.TransactionID, &v.GatewayTransactionID,
		&v.Layer, &v.Cause, &v.Confidence, &v.Reasoning,
		&v.RecommendedAction, &v.ModelVersion,
		&v.StatusCode, &v.NPCIResponseCode, &v.BankResponseCode,
		&v.Amount, &v.CustomerBank, &v.RetryCountSoFar,
		&v.CreatedAt,
	)
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("classification %s not found", id)
		}
		return nil, fmt.Errorf("get classification: %w", err)
	}
	return &v, nil
}
