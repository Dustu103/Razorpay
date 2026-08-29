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
	"sync"
	"time"

	"razorpay-classification-service/internal/models"
)

const (
	groqAPIURL     = "https://api.groq.com/openai/v1/chat/completions"
	groqModel      = "openai/gpt-oss-120b"
	geminiModel    = "gemini-flash-latest"
	requestTimeout = 10 * time.Second
)

// --- OpenAI / Groq Structs ---
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

type groqResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

// --- Gemini Structs ---
type geminiRequest struct {
	Contents          []geminiContent `json:"contents"`
	SystemInstruction *geminiContent  `json:"systemInstruction,omitempty"`
	GenerationConfig  geminiConfig    `json:"generationConfig"`
}

type geminiContent struct {
	Parts []geminiPart `json:"parts"`
}

type geminiPart struct {
	Text string `json:"text"`
}

type geminiConfig struct {
	Temperature      float64 `json:"temperature"`
	ResponseMimeType string  `json:"responseMimeType"`
}

type geminiResponse struct {
	Candidates []struct {
		Content struct {
			Parts []struct {
				Text string `json:"text"`
			} `json:"parts"`
		} `json:"content"`
	} `json:"candidates"`
}

// --- Common ---
type llmOutput struct {
	Cause             string  `json:"cause"`
	RecommendedAction string  `json:"recommended_action"`
	Confidence        float64 `json:"confidence"`
	Reasoning         string  `json:"reasoning"`
}

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
		txn.StatusCode, br, nr, txn.Amount, cb, txn.RetryCountSoFar,
		txn.MandateNotificationSentAt != nil, txn.DebitScheduledAt != nil,
	)
}

// Classify hits both Groq and Gemini concurrently and returns the best response.
func Classify(txn *models.Transaction) (*models.ClassificationResult, error) {
	groqKey := os.Getenv("GROQ_API_KEY")
	geminiKey := os.Getenv("GEMINI_API_KEY")

	if groqKey == "" && geminiKey == "" {
		log.Printf("[layer3] No LLM API keys set — using heuristic fallback for txn=%s", txn.ID)
		return heuristicFallback(txn), nil
	}

	var wg sync.WaitGroup
	var groqRes, geminiRes *models.ClassificationResult

	if groqKey != "" {
		wg.Add(1)
		go func() {
			defer wg.Done()
			res, err := callGroq(groqKey, txn)
			if err == nil {
				groqRes = res
			} else {
				log.Printf("[layer3] Groq error for txn=%s: %v", txn.ID, err)
			}
		}()
	}

	if geminiKey != "" {
		wg.Add(1)
		go func() {
			defer wg.Done()
			res, err := callGemini(geminiKey, txn)
			if err == nil {
				geminiRes = res
			} else {
				log.Printf("[layer3] Gemini error for txn=%s: %v", txn.ID, err)
			}
		}()
	}

	wg.Wait()

	if groqRes == nil && geminiRes == nil {
		log.Printf("[layer3] All LLM calls failed for txn=%s — using heuristic fallback", txn.ID)
		return heuristicFallback(txn), nil
	}

	if groqRes != nil && geminiRes == nil {
		return groqRes, nil
	}
	if geminiRes != nil && groqRes == nil {
		return geminiRes, nil
	}

	// Multi-LLM Resolution: Pick the one with the higher confidence!
	if groqRes.Confidence > geminiRes.Confidence {
		groqRes.Reasoning = "[Layer 3 · Multi-LLM Win: Groq] " + groqRes.Reasoning
		return groqRes, nil
	}
	
	geminiRes.Reasoning = "[Layer 3 · Multi-LLM Win: Gemini] " + geminiRes.Reasoning
	return geminiRes, nil
}

func callGroq(apiKey string, txn *models.Transaction) (*models.ClassificationResult, error) {
	payload := groqRequest{
		Model: groqModel,
		Messages: []chatMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: buildUserPrompt(txn)},
		},
		Temperature: 0.1,
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
		return nil, fmt.Errorf("http call: %w", err)
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API returned %d: %s", resp.StatusCode, string(respBytes))
	}

	var groqResp groqResponse
	if err := json.Unmarshal(respBytes, &groqResp); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w", err)
	}
	if len(groqResp.Choices) == 0 {
		return nil, fmt.Errorf("returned no choices")
	}

	raw := strings.TrimSpace(groqResp.Choices[0].Message.Content)

	var out llmOutput
	if err := json.Unmarshal([]byte(raw), &out); err != nil {
		return nil, fmt.Errorf("parse JSON output: %w (raw: %s)", err, raw)
	}

	if out.Confidence > 1.0 { out.Confidence = 1.0 }
	if out.Confidence < 0.0 { out.Confidence = 0.0 }

	version := groqModel
	return &models.ClassificationResult{
		TransactionID:     txn.ID,
		Layer:             3,
		Cause:             out.Cause,
		Confidence:        out.Confidence,
		Reasoning:         out.Reasoning,
		RecommendedAction: out.RecommendedAction,
		ModelVersion:      &version,
	}, nil
}

func callGemini(apiKey string, txn *models.Transaction) (*models.ClassificationResult, error) {
	url := fmt.Sprintf("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s", geminiModel, apiKey)

	payload := geminiRequest{
		Contents: []geminiContent{
			{Parts: []geminiPart{{Text: buildUserPrompt(txn)}}},
		},
		SystemInstruction: &geminiContent{
			Parts: []geminiPart{{Text: systemPrompt}},
		},
		GenerationConfig: geminiConfig{
			Temperature:      0.1,
			ResponseMimeType: "application/json",
		},
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), requestTimeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http call: %w", err)
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API returned %d: %s", resp.StatusCode, string(respBytes))
	}

	var geminiResp geminiResponse
	if err := json.Unmarshal(respBytes, &geminiResp); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w", err)
	}
	if len(geminiResp.Candidates) == 0 || len(geminiResp.Candidates[0].Content.Parts) == 0 {
		return nil, fmt.Errorf("returned no choices")
	}

	raw := strings.TrimSpace(geminiResp.Candidates[0].Content.Parts[0].Text)

	var out llmOutput
	if err := json.Unmarshal([]byte(raw), &out); err != nil {
		return nil, fmt.Errorf("parse JSON output: %w (raw: %s)", err, raw)
	}

	if out.Confidence > 1.0 { out.Confidence = 1.0 }
	if out.Confidence < 0.0 { out.Confidence = 0.0 }

	version := geminiModel
	return &models.ClassificationResult{
		TransactionID:     txn.ID,
		Layer:             3,
		Cause:             out.Cause,
		Confidence:        out.Confidence,
		Reasoning:         out.Reasoning,
		RecommendedAction: out.RecommendedAction,
		ModelVersion:      &version,
	}, nil
}

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
		reasoning = "[Layer 3 · Heuristic Fallback] Defaulting to soft decline for safe retry. LLM API Keys missing or rate limited."
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
