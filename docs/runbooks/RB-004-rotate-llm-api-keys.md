# RB-004: Rotate LLM API Keys

**Trigger:** Groq or Gemini API key has expired, been revoked, or is returning consistent `401 Unauthorized`.  
**Severity:** Medium — the system degrades to heuristic fallback but does not crash.

---

## Symptoms

- Worker logs show: `ERROR layer3: groq request failed: 401 Unauthorized`
- Live accuracy drops to ~46–65% (ML-only / heuristic fallback range).
- Dashboard reasoning text shows: `heuristic: soft_decline` instead of an LLM-generated explanation.

---

## Steps

### 1. Identify which key is failing

Check the logs:
```bash
docker compose logs --tail=100 classification-service | grep -E "(401|403|api key)"
```

### 2. Generate a new API key

**Groq:**
1. Go to [https://console.groq.com/keys](https://console.groq.com/keys).
2. Click **Create API Key**.
3. Copy the new key.

**Gemini:**
1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
2. Click **Create API Key**.
3. Copy the new key.

### 3. Update the `.env` file

```bash
# In the project root .env file:
GROQ_API_KEY=gsk_NEW_KEY_HERE
GEMINI_API_KEY=AIzaSy_NEW_KEY_HERE
```

> ⚠️ **Never commit `.env` to version control.** It is listed in `.gitignore`.

### 4. Restart the classification service to pick up the new keys

```bash
docker compose up -d --force-recreate classification-service
```

### 5. Verify the new key is working

```bash
docker compose logs -f classification-service
```
Look for successful LLM calls:
```
INFO  layer3: groq responded with cause=gateway_fault confidence=0.91
```

### 6. Run a quick E2E validation (see RB-003)

---

## Security Note

API keys are injected at runtime via environment variables only. They are never hard-coded in source files or committed to the repository. The `.env` file is in `.gitignore`. In a production environment, keys should be stored in a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager) and injected at container startup.
