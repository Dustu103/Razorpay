package db

import (
	"context"
	"fmt"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"razorpay-nach-recovery-service/internal/models"
)

type DB struct {
	Pool *pgxpool.Pool
}

func Connect(ctx context.Context) (*DB, error) {
	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		databaseURL = "postgres://razorpay:razorpay@postgres:5432/razorpay_classifier?sslmode=disable"
	}

	config, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		return nil, fmt.Errorf("parse database url: %w", err)
	}

	config.MaxConns = 10
	config.MinConns = 2
	config.MaxConnLifetime = 30 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, fmt.Errorf("connect to postgres: %w", err)
	}

	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping postgres: %w", err)
	}

	return &DB{Pool: pool}, nil
}

func (d *DB) Close() {
	if d.Pool != nil {
		d.Pool.Close()
	}
}

// GetFailedNACHTransactions retrieves pending NACH mandate failures for processing
func (d *DB) GetFailedNACHTransactions(ctx context.Context, limit int) ([]models.MandateTransaction, error) {
	query := `
		SELECT 
			id,
			COALESCE(payment_rail, 'nach'),
			COALESCE(product_type, 'sip'),
			amount,
			COALESCE(error_code, 'insufficient_funds'),
			COALESCE(consecutive_failure_count, 1),
			days_since_due_date,
			created_at
		FROM transactions
		WHERE payment_rail = 'nach'
		ORDER BY created_at DESC
		LIMIT $1
	`
	rows, err := d.Pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("query nach transactions: %w", err)
	}
	defer rows.Close()

	var txns []models.MandateTransaction
	for rows.Next() {
		var t models.MandateTransaction
		if err := rows.Scan(
			&t.ID,
			&t.PaymentRail,
			&t.ProductType,
			&t.MandateValue,
			&t.Cause,
			&t.ConsecutiveFailureCount,
			&t.DaysSinceDueDate,
			&t.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("scan nach transaction: %w", err)
		}
		txns = append(txns, t)
	}
	return txns, nil
}
