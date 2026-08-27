package load

import (
	"bytes"
	"fmt"
	"net/http"
	"sync"
	"testing"
	"time"
)

const webhookURL = "http://localhost:3001/api/v1/webhook"
const numRequests = 1000
const concurrency = 50

func TestLoad_IngestionAPI(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping load test in short mode")
	}

	var wg sync.WaitGroup
	requests := make(chan int, numRequests)
	
	// Start workers
	start := time.Now()
	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			for reqID := range requests {
				txnID := fmt.Sprintf("load-%d-%d", start.UnixNano(), reqID)
				
				// A payload that triggers L1 (no notification) to avoid hitting the L3 LLM rate limit on a free tier
				payload := []byte(fmt.Sprintf(`{
					"event": "payment.failed",
					"payload": {
						"payment": {
							"entity": {
								"id": "%s",
								"status_code": "FAILED",
								"amount": 50000,
								"debit_scheduled_at": "2026-08-28T10:00:00Z"
							}
						}
					}
				}`, txnID))
				
				resp, err := http.Post(webhookURL, "application/json", bytes.NewBuffer(payload))
				if err != nil {
					t.Errorf("Request failed: %v", err)
					continue
				}
				resp.Body.Close()
				if resp.StatusCode != 202 {
					t.Errorf("Expected 202, got %d", resp.StatusCode)
				}
			}
		}(i)
	}

	// Feed jobs
	for i := 0; i < numRequests; i++ {
		requests <- i
	}
	close(requests)

	// Wait for all requests to finish
	wg.Wait()
	duration := time.Since(start)

	reqPerSec := float64(numRequests) / duration.Seconds()
	t.Logf("Load test complete: %d requests in %v (%.2f req/sec)", numRequests, duration, reqPerSec)
	
	if reqPerSec < 50 {
		t.Fatalf("Ingestion throughput too low: %.2f req/sec. Expected > 50", reqPerSec)
	}
}
