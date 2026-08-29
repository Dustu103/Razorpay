# Reason code evidence mapping for Visa, Mastercard, and RuPay (grounded in reference datasets)

REASON_CODE_EVIDENCE_MAP = {
    # Visa (10.x and 13.x series)
    "visa_10.4": {
        "network": "visa",
        "title": "Other Fraud - Card Absent Environment",
        "winnability": "high_if_3ds",
        "deadline_days": 14,
        "required_evidence": ["has_3ds_auth", "has_ip_device_fingerprint", "has_avs_cvv_match"],
        "checklist": [
            "Verify IP address and device fingerprint match historic purchases",
            "Ensure 3D Secure verification logs are fully attached",
            "Verify Address Verification Service (AVS) and CVV match results"
        ]
    },
    "visa_13.1": {
        "network": "visa",
        "title": "Merchandise/Services Not Received",
        "winnability": "medium",
        "deadline_days": 14,
        "required_evidence": ["has_delivery_proof"],
        "checklist": [
            "Attach official shipping carrier tracking logs showing 'Delivered'",
            "Verify the delivery address matches the customer billing profile"
        ]
    },
    "visa_13.3": {
        "network": "visa",
        "title": "Not as Described or Defective",
        "winnability": "medium",
        "deadline_days": 14,
        "required_evidence": ["has_prior_comms"],
        "checklist": [
            "Attach clear customer service interaction logs",
            "Provide proof of merchant return/refund policy shown at checkout"
        ]
    },

    # Mastercard (48xx series)
    "mc_4837": {
        "network": "mastercard",
        "title": "No Cardholder Authorization",
        "winnability": "high_if_3ds",
        "deadline_days": 14,
        "required_evidence": ["has_avs_cvv_match", "has_3ds_auth", "has_signed_receipt"],
        "checklist": [
            "Provide signed checkout receipt if digital signature is present",
            "Verify AVS/CVV matches and attach authorization confirmation logs",
            "Check 3DS logs for successful cardholder verification"
        ]
    },
    "mc_4853": {
        "network": "mastercard",
        "title": "Cardholder Dispute (Goods/Services Not Provided)",
        "winnability": "medium",
        "deadline_days": 14,
        "required_evidence": ["has_delivery_proof", "has_usage_logs", "has_prior_comms"],
        "checklist": [
            "Attach shipping delivery confirmations or digital service consumption logs",
            "Provide proof of user login/account activity post-transaction date"
        ]
    },
    "mc_4808": {
        "network": "mastercard",
        "title": "Authorization-Related Chargeback",
        "winnability": "low",
        "deadline_days": 14,
        "required_evidence": [],
        "checklist": [
            "Provide proof of a valid authorization code approved prior to capture"
        ]
    },

    # RuPay (NPCI global clearing codes)
    "rupay_ru01": {
        "network": "rupay",
        "title": "Unauthorized Transaction",
        "winnability": "medium",
        "deadline_days": 7,
        "required_evidence": ["has_ip_device_fingerprint"],
        "checklist": [
            "Provide 2FA/OTP authentication logs",
            "Attach IP and device details recorded during the payment flow"
        ]
    },
    "rupay_ru02": {
        "network": "rupay",
        "title": "Goods/Services Not Received",
        "winnability": "medium",
        "deadline_days": 7,
        "required_evidence": ["has_delivery_proof"],
        "checklist": [
            "Attach tracking receipts showing delivery confirmation"
        ]
    },
    "rupay_ru03": {
        "network": "rupay",
        "title": "Duplicate Transaction",
        "winnability": "high",
        "deadline_days": 7,
        "required_evidence": [],
        "checklist": [
            "Provide explicit transaction logs showing distinct orders for both payments"
        ]
    },
    "rupay_1062": {
        "network": "rupay",
        "title": "Goods/Services Not as Described / Defective",
        "winnability": "medium",
        "deadline_days": 7,
        "required_evidence": ["has_prior_comms"],
        "checklist": [
            "Provide customer conversation history demonstrating attempts to resolve"
        ]
    },
    "rupay_1064": {
        "network": "rupay",
        "title": "Goods/Services Not Provided / Cancelled",
        "winnability": "medium",
        "deadline_days": 7,
        "required_evidence": ["has_delivery_proof", "has_signed_receipt"],
        "checklist": [
            "Attach delivery tracking logs and physical/digital signature confirmation"
        ]
    },
    "rupay_1065": {
        "network": "rupay",
        "title": "Account Debited but Confirmation Not Received",
        "winnability": "low",
        "deadline_days": 5,
        "required_evidence": [],
        "checklist": [
            "Provide merchant ledger reconciliation records",
            "Attach internal gateway transaction status showing failure/reversal"
        ]
    },
    "rupay_1085": {
        "network": "rupay",
        "title": "Charged More Than Transaction Amount",
        "winnability": "high",
        "deadline_days": 7,
        "required_evidence": [],
        "checklist": [
            "Attach invoice or pricing ledgers to justify the charged amount"
        ]
    }
}
