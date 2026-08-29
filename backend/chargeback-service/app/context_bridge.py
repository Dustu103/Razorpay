from .reason_code_map import REASON_CODE_EVIDENCE_MAP

def build_context_prompt(dispute_data: dict, top_shap_features: list) -> tuple[str, str]:
    """
    Constrains prompt generation. Injecting rules dynamically into system/user prompts.
    Preventing statistical leaking in drafted text.
    """
    code = dispute_data.get("reason_code")
    rules = REASON_CODE_EVIDENCE_MAP.get(code)
    if not rules:
        raise ValueError(f"Unknown reason code: {code}")

    network = rules["network"].upper()
    title = rules["title"]
    required = rules["required_evidence"]
    checklist = rules["checklist"]

    # 1. Map present evidence fields to true/false text
    evidence_status = []
    for field in required:
        val = dispute_data.get(field, 0)
        status_txt = "AVAILABLE (VERIFIED)" if val == 1 else "NOT AVAILABLE"
        evidence_status.append(f"- {field}: {status_txt}")
    
    evidence_txt = "\n".join(evidence_status) if evidence_status else "- No specific evidence required."

    # 2. Checklist items formatted for LLM compliance guidance
    checklist_txt = "\n".join(f"- {item}" for item in checklist)

    # 3. Create context around top SHAP features
    shap_highlights = []
    for feat in top_shap_features:
        # Map feature name to readable explanation
        if feat == "has_3ds_auth":
            shap_highlights.append("3D Secure authentication (crucial for liability shift)")
        elif feat == "has_ip_device_fingerprint":
            shap_highlights.append("IP address and device fingerprint validation")
        elif feat == "has_avs_cvv_match":
            shap_highlights.append("AVS / CVV matching status")
        elif feat == "has_delivery_proof":
            shap_highlights.append("Official delivery/tracking logs")
        elif feat == "has_prior_comms":
            shap_highlights.append("Prior merchant-to-customer communication records")
        elif feat == "days_remaining":
            shap_highlights.append("Urgency of response deadline")
        elif feat == "repeat_dispute_count":
            shap_highlights.append("History of repeat disputes by the customer")

    shap_txt = ", ".join(shap_highlights) if shap_highlights else "evidence completeness"

    system_prompt = f"""You are a professional payment dispute arbitration agent drafting a chargeback representment narrative for the {network} card network.

Your goal is to draft a clean, formal, persuasive rebuttal letter addressed to the issuing bank/arbitrator.
Your response MUST STRICTLY follow these network compliance guidelines for reason code {code} ({title}):
{checklist_txt}

CRITICAL INSTRUCTIONS:
- You must structure your argument strictly around the card network's adjudication rules.
- Do NOT mention any machine learning terms, SHAP values, prediction scores, confidence levels, or win probabilities in the narrative.
- Rely ONLY on the verified evidence status provided in the context. Do not make up mock tracking numbers, customer names, or transaction details unless they are explicitly provided.
- Format the response as a professional business letter. Start with 'Subject: Representment Rebuttal - Reason Code {code}' and write a structured, logical narrative.
"""

    user_prompt = f"""Transaction Metadata:
- Network: {network}
- Reason Code: {code} ({title})
- Transaction Amount (INR): {dispute_data.get('transaction_amount_inr', 'N/A')}
- Days Since Transaction: {dispute_data.get('days_since_transaction', 'N/A')}
- Days Remaining to Respond: {dispute_data.get('days_remaining', 'N/A')}
- Customer Repeat Dispute Count: {dispute_data.get('repeat_dispute_count', 0)}

Verified Evidence Status:
{evidence_txt}

Arbitration Highlights (Focus heavily on these factors in your narrative):
- Rebuttal should emphasize: {shap_txt}
"""

    return system_prompt, user_prompt
