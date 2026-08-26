// Package layer3 implements the general-purpose LLM fallback classifier.
// It is invoked when Layer 2's confidence falls below the action-specific threshold.
//
// Provider: Groq (groq.com) — free tier, OpenAI-compatible API.
// Model: llama-3.1-70b-versatile (free, high accuracy for structured classification)
// Set GROQ_API_KEY in environment. Get a free key at: https://console.groq.com
package layer3

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"razorpay-classification-service/internal/models"
)

const (
	groqAPIURL    = "https://api.groq.com/openai/v1/chat/completions"
	groqModel     = "openai/gpt-oss-120b"
	requestTimeout = 45 * time.Second
)

// groqRequest mirrors the OpenAI /chat/completions request body.
type groqRequest struct {
	Model       string        `json:"model"`
	Messages    []chatMessage `json:"messages"`
	Temperature float64       `json:"temperature"`
	MaxTokens   int           `json:"max_tokens"`
}

type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// groqResponse mirrors the relevant parts of the OpenAI response.
type groqResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

// llmOutput is what we parse from the LLM's JSON reply.
type llmOutput struct {
	Cause             string  `json:"cause"`
	RecommendedAction string  `json:"recommended_action"`
	Confidence        float64 `json:"confidence"`
	Reasoning         string  `json:"reasoning"`
}

// systemPrompt defines the classifier's role and output schema.
const systemPrompt = `You are a payment-failure root-cause classifier for a Razorpay mandate system.
You will receive a JSON payload describing a failed payment transaction.
Your task is to classify the failure into exactly ONE of these five causes:
  - notification_compliance_block
  - soft_decline
  - hard_decline
  - gateway_fault
  - fraud_filter_block

Then recommend exactly ONE action from:
  - silent_reschedule
  - retry_scheduled
  - retry_now
  - do_not_retry
  - reverify_and_reverse

Rules:
- notification_compliance_block is ONLY for RBI pre-debit notification violations (24-hour window). Use silent_reschedule.
- soft_decline: transient failures (funds, temp issuer issues). Use retry_scheduled or retry_now.
- hard_decline: permanent card issues (expired, blocked, invalid). Use do_not_retry.
- gateway_fault: network/timeout failures unrelated to card/issuer. Use retry_now or retry_scheduled.
- fraud_filter_block: fraud/risk flags from bank or gateway. Use do_not_retry or reverify_and_reverse (only if certain).

Respond ONLY with valid JSON matching this exact schema (no markdown, no explanation outside JSON):
{
  "cause": "<one of the five causes>",
  "recommended_action": "<one of the five actions>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<1-3 sentence human-readable explanation for the audit trail>"
}`

// buildUserPrompt serializes the transaction into a prompt payload.
func buildUserPrompt(txn *models.Transaction) string {
	br := "null"
	if txn.BankResponseCode != nil {
		br = fmt.Sprintf("%q", *txn.BankResponseCode)
	}
	nr := "null"
	if txn.NPCIResponseCode != nil {
		nr = fmt.Sprintf("%q", *txn.NPCIResponseCode)
	}
	cb := "null"
	if txn.CustomerBank != nil {
		cb = fmt.Sprintf("%q", *txn.CustomerBank)
	}

	return fmt.Sprintf(`{
  "status_code": %q,
  "bank_response_code": %s,
  "npci_response_code": %s,
  "amount_paise": %.0f,
  "customer_bank": %s,
  "retry_count_so_far": %d,
  "has_mandate_notification": %v,
  "has_debit_schedule": %v
}`,
		txn.StatusCode,
		br, nr,
		txn.Amount,
		cb,
		txn.RetryCountSoFar,
		txn.MandateNotificationSentAt != nil,
		txn.DebitScheduledAt != nil,
	)
}

// Classify calls the Groq API and parses the structured LLM output.
// Falls back to a heuristic result if the API key is not set or the call fails.
func Classify(txn *models.Transaction) (*models.ClassificationResult, error) {
	apiKey := os.Getenv("GROQ_API_KEY")
	if apiKey == "" {
		log.Printf("[layer3] GROQ_API_KEY not set — using heuristic fallback for txn=%s", txn.ID)
		return heuristicFallback(txn), nil
	}

	result, err := callGroq(apiKey, txn)
	if err != nil {
		log.Printf("[layer3] Groq API error for txn=%s: %v — using heuristic fallback", txn.ID, err)
		return heuristicFallback(txn), nil
	}
	return result, nil
}

// callGroq performs the actual HTTP call to Groq's API.
func callGroq(apiKey string, txn *models.Transaction) (*models.ClassificationResult, error) {
	payload := groqRequest{
		Model: groqModel,
		Messages: []chatMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: buildUserPrompt(txn)},
		},
		Temperature: 0.1, // Low temperature → more deterministic classifications
		MaxTokens:   512,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), requestTimeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, groqAPIURL, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("groq http call: %w", err)
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("groq API returned %d: %s", resp.StatusCode, string(respBytes))
	}

	var groqResp groqResponse
	if err := json.Unmarshal(respBytes, &groqResp); err != nil {
		return nil, fmt.Errorf("unmarshal groq response: %w", err)
	}
	if len(groqResp.Choices) == 0 {
		return nil, fmt.Errorf("groq returned no choices")
	}

	raw := strings.TrimSpace(groqResp.Choices[0].Message.Content)

	var out llmOutput
	if err := json.Unmarshal([]byte(raw), &out); err != nil {
		return nil, fmt.Errorf("parse LLM JSON output: %w (raw: %s)", err, raw)
	}

	// Sanitize confidence bounds
	if out.Confidence > 1.0 { out.Confidence = 1.0 }
	if out.Confidence < 0.0 { out.Confidence = 0.0 }

	version := groqModel
	return &models.ClassificationResult{
		TransactionID:     txn.ID,
		Layer:             3,
		Cause:             out.Cause,
		Confidence:        out.Confidence,
		Reasoning:         fmt.Sprintf("[Layer 3 · GPT-OSS-120B via Groq] %s", out.Reasoning),
		RecommendedAction: out.RecommendedAction,
		ModelVersion:      &version,
	}, nil
}

// heuristicFallback is used when GROQ_API_KEY is not set or the API call fails.
// This ensures the pipeline never blocks — it degrades gracefully.
func heuristicFallback(txn *models.Transaction) *models.ClassificationResult {
	var cause, action, reasoning string

	switch {
	case txn.BankResponseCode != nil && (*txn.BankResponseCode == "59" || *txn.BankResponseCode == "57"):
		cause = models.CauseFraudFilterBlock
		action = models.ActionDoNotRetry
		reasoning = "[Layer 3 · Heuristic Fallback] Bank response code indicates a fraud or risk filter block. Manual review recommended."
	case txn.StatusCode == "GATEWAY_ERROR" || txn.StatusCode == "TIMEOUT":
		cause = models.CauseGatewayFault
		action = models.ActionRetryNow
		reasoning = "[Layer 3 · Heuristic Fallback] Gateway-level failure. Safe to retry immediately."
	default:
		cause = models.CauseSoftDecline
		action = models.ActionRetryScheduled
		reasoning = "[Layer 3 · Heuristic Fallback] Defaulting to soft decline for safe retry. GROQ_API_KEY not configured — set it to enable full LLM analysis."
	}

	version := "heuristic-fallback"
	return &models.ClassificationResult{
		TransactionID:     txn.ID,
		Layer:             3,
		Cause:             cause,
		Confidence:        0.60,
		Reasoning:         reasoning,
		RecommendedAction: action,
		ModelVersion:      &version,
	}
}
