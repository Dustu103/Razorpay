package queue

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"razorpay-ingestion-service/internal/models"

	"github.com/redis/go-redis/v9"
)

type Queue struct {
	client    *redis.Client
	queueName string
}

func New() (*Queue, error) {
	url := os.Getenv("REDIS_URL")
	if url == "" {
		return nil, fmt.Errorf("REDIS_URL is not set")
	}
	queueName := os.Getenv("QUEUE_NAME")
	if queueName == "" {
		queueName = "classification_jobs"
	}

	opts, err := redis.ParseURL(url)
	if err != nil {
		return nil, fmt.Errorf("redis.ParseURL: %w", err)
	}
	client := redis.NewClient(opts)

	if err := client.Ping(context.Background()).Err(); err != nil {
		return nil, fmt.Errorf("redis ping: %w", err)
	}
	return &Queue{client: client, queueName: queueName}, nil
}

func (q *Queue) Close() error { return q.client.Close() }

// Enqueue pushes a ClassificationJob to the Redis list (RPUSH = tail of queue).
func (q *Queue) Enqueue(ctx context.Context, job models.ClassificationJob) error {
	data, err := json.Marshal(job)
	if err != nil {
		return fmt.Errorf("marshal job: %w", err)
	}
	if err := q.client.RPush(ctx, q.queueName, data).Err(); err != nil {
		return fmt.Errorf("rpush: %w", err)
	}
	return nil
}
