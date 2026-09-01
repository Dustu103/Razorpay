import os
from pydantic import BaseModel
from typing import Optional

# Use native groq SDK — no LangChain overhead
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# ─── I/O Schemas ──────────────────────────────────────────────────────────────

class B2BInvoiceInput(BaseModel):
    id: str
    customer_name: str
    amount_due: float
    is_msme_registered: bool
    days_late: int

class B2BInvoiceOutput(BaseModel):
    action: str
    tax_rule_triggered: str
    draft_email_body: str

# ─── Statute Definitions ───────────────────────────────────────────────────────

STATUTE_43B = {
    "name": "Section 43B(h) of the Income Tax Act, 1961",
    "threshold_days": 45,
    "penalty": "disallowance of the full expense as a tax deduction in the current Assessment Year",
    "action": "tax_lever_43B",
    "rule_label": "Sec 43B(h) Penalty",
}

STATUTE_RULE37 = {
    "name": "Rule 37 of the CGST Rules, 2017",
    "threshold_days": 180,
    "penalty": "mandatory reversal of Input Tax Credit (ITC) already claimed, plus interest under Section 50 and penalties under Section 122 of the CGST Act",
    "action": "tax_lever_GST",
    "rule_label": "CGST Rule 37 – ITC Reversal",
}

# ─── Deterministic Router ─────────────────────────────────────────────────────

def route_invoice(data: B2BInvoiceInput) -> Optional[dict]:
    """
    Pure deterministic compliance routing.
    Returns the applicable statute dict or None if no threshold is breached.
    Rule 37 (180 days) takes priority over Sec 43B (45 days MSME).
    """
    if data.days_late >= STATUTE_RULE37["threshold_days"]:
        return STATUTE_RULE37
    if data.days_late >= STATUTE_43B["threshold_days"] and data.is_msme_registered:
        return STATUTE_43B
    return None


def _escalation_action(days_late: int) -> str:
    """Non-tax escalation path for invoices that don't hit statutory thresholds."""
    if days_late >= 30:
        return "escalated_email"
    if days_late >= 7:
        return "gentle_sms"
    return "no_action"


# ─── Groq LLM Drafter ─────────────────────────────────────────────────────────

def _draft_email(data: B2BInvoiceInput, statute: dict) -> str:
    """
    Uses Groq Llama 3 70B to draft a formal legal notice.
    Falls back to a deterministic template if GROQ_API_KEY is not set.
    """
    api_key = os.getenv("GROQ_API_KEY")

    if GROQ_AVAILABLE and api_key:
        try:
            client = Groq(api_key=api_key)
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert Indian corporate lawyer and accounts receivable manager. "
                            "You write formal, polite, but firm legal notices. "
                            "Do NOT invent any facts not explicitly provided. "
                            "Keep the email to exactly 3 short paragraphs."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Draft a formal legal notice email for the following overdue invoice:\n"
                            f"- Customer: {data.customer_name}\n"
                            f"- Invoice ID: {data.id}\n"
                            f"- Amount Due: ₹{data.amount_due:,.0f}\n"
                            f"- Days Overdue: {data.days_late}\n"
                            f"- Applicable Statute: {statute['name']}\n"
                            f"- Consequence of Non-Payment: {statute['penalty']}\n\n"
                            f"The email must:\n"
                            f"1. State the overdue amount and days.\n"
                            f"2. Cite the exact statute and the legal consequence for the buyer.\n"
                            f"3. Request immediate payment and ask for a payment timeline.\n"
                            f"Sign off as 'Accounts Receivable Team'."
                        ),
                    },
                ],
                model="llama3-70b-8192",
                temperature=0.3,
                max_tokens=512,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"[b2b_agent] Groq call failed: {e}. Using fallback template.")

    # Deterministic fallback template (no API key required)
    return (
        f"Dear Finance Team,\n\n"
        f"This is a formal notice regarding Invoice {data.id} for ₹{data.amount_due:,.0f} "
        f"which has been outstanding for {data.days_late} days.\n\n"
        f"Under {statute['name']}, this delay triggers {statute['penalty']}. "
        f"We strongly urge immediate settlement to avoid these adverse consequences.\n\n"
        f"Kindly confirm your payment timeline at the earliest.\n\n"
        f"Regards,\nAccounts Receivable Team"
    )


# ─── Main Agent ──────────────────────────────────────────────────────────────

class B2BAgentModel:
    """
    The B2B Tax Lever Agent.
    Routes deterministically, then uses Groq LLM for email drafting.
    """

    def predict(self, data: B2BInvoiceInput) -> B2BInvoiceOutput:
        statute = route_invoice(data)

        if statute is None:
            # Below all statutory thresholds — use standard escalation
            return B2BInvoiceOutput(
                action=_escalation_action(data.days_late),
                tax_rule_triggered="",
                draft_email_body="",
            )

        email_body = _draft_email(data, statute)

        return B2BInvoiceOutput(
            action=statute["action"],
            tax_rule_triggered=statute["rule_label"],
            draft_email_body=email_body,
        )
