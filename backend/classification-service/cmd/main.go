package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"razorpay-classification-service/internal/db"
	"razorpay-classification-service/internal/worker"

	"github.com/redis/go-redis/v9"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	// ── Database ──────────────────────────────────────────────────────────
	database, err := db.Connect(ctx)
	if err != nil {
		log.Fatalf("[classification-service] db connect: %v", err)
	}
	defer database.Close()
	log.Println("[classification-service] Postgres connected")

	// ── Redis ─────────────────────────────────────────────────────────────
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		log.Fatal("[classification-service] REDIS_URL is not set")
	}
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("[classification-service] redis parse url: %v", err)
	}
	redisClient := redis.NewClient(opts)
	if err := redisClient.Ping(ctx).Err(); err != nil {
		log.Fatalf("[classification-service] redis ping: %v", err)
	}
	defer redisClient.Close()
	log.Println("[classification-service] Redis connected")

	// ── Worker loop ───────────────────────────────────────────────────────
	w := worker.New(database, redisClient)
	w.Run(ctx) // blocks until context is cancelled (SIGTERM/SIGINT)

	log.Println("[classification-service] stopped")
}
