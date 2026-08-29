package unit

import (
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"razorpay-classification-service/internal/layer2"
	"razorpay-classification-service/internal/models"
)

func TestLayer2_Classify_Mocked(t *testing.T) {
	mockMLServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{
			"transaction_id": "txn-l2-1",
			"layer": 2,
			"cause": "fraud_filter_block",
			"confidence": 0.95,
			"reasoning": "mock reasoning",
			"recommended_action": "do_not_retry",
			"model_version": "mock-v1"
		}`))
	}))
	defer mockMLServer.Close()

	os.Setenv("ML_SERVICE_URL", mockMLServer.URL)
	defer os.Unsetenv("ML_SERVICE_URL")

	txn := &models.Transaction{
		ID: "txn-l2-1",
	}

	res, err := layer2.Classify(txn)
	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}
	if res.Cause != models.CauseFraudFilterBlock {
		t.Errorf("Expected fraud block, got %s", res.Cause)
	}
}
