# Runbooks

> Operational runbooks for on-call engineers and developers. Each runbook covers a specific failure scenario with step-by-step remediation.

## Index

| Runbook | Trigger |
|---------|---------|
| [RB-001: Restart the Classification Worker](./RB-001-restart-classification-worker.md) | Worker is stuck or not consuming jobs from Redis |
| [RB-002: Debug a Stuck Redis Queue](./RB-002-debug-stuck-redis-queue.md) | Jobs are piling up in Redis but not being processed |
| [RB-003: Run the E2E Test Pipeline](./RB-003-run-e2e-test-pipeline.md) | Validate the full pipeline after a deployment |
| [RB-004: Rotate LLM API Keys](./RB-004-rotate-llm-api-keys.md) | Groq or Gemini API key has expired or been revoked |
