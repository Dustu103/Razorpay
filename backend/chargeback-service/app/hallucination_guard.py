import re

# Regex patterns for validation
PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PROBABILITY_PATTERN = re.compile(r'\b(probability|accuracy|model|xgb|xgboost|random forest|lightgbm|machine learning|auc|f1|classifier)\b', re.IGNORECASE)

def clean_hallucinations(narrative: str) -> tuple[str, list[str]]:
    """
    Strips LLM hallucinations and compliance leaks.
    Returns: (cleaned_narrative, list_of_redactions)
    """
    redactions = []
    cleaned = narrative

    # 1. Strip ML internal statistics and metrics leak
    if PROBABILITY_PATTERN.search(cleaned):
        cleaned = PROBABILITY_PATTERN.sub("[REDACTED_ML_METRIC]", cleaned)
        redactions.append("Internal ML metrics leaked in narrative")

    # 2. Redact ungrounded email address placeholders (except common mock domains if needed, but better to be safe)
    emails = EMAIL_PATTERN.findall(cleaned)
    for email in emails:
        cleaned = cleaned.replace(email, "[REDACTED_EMAIL]")
        redactions.append(f"Redacted ungrounded email: {email}")

    # 3. Redact ungrounded phone number placeholders
    phones = PHONE_PATTERN.findall(cleaned)
    for phone in phones:
        cleaned = cleaned.replace(phone, "[REDACTED_PHONE]")
        redactions.append(f"Redacted ungrounded phone number: {phone}")

    # 4. Remove system prompt leaking artifacts (e.g. "Draft representment narrative", "As an AI...")
    system_patterns = [
        r"(?i)As an AI (assistant|writing assistant),? I (have drafted|am drafting)...",
        r"(?i)Here is a (draft|representment narrative) of the...",
        r"(?i)SYSTEM:\s*",
        r"(?i)USER:\s*"
    ]
    for pattern in system_patterns:
        match = re.search(pattern, cleaned)
        if match:
            cleaned = re.sub(pattern, "", cleaned)
            redactions.append(f"Removed system leak artifact: '{match.group(0)}'")

    return cleaned.strip(), redactions
