"""
E2E Test: NACH Mandate Recovery Service
=======================================
Tests nach-recovery-service HTTP API and Governor Engine:
1. GET /health on port 3007
2. GET /api/v1/nach-metrics on port 3007
3. POST /api/v1/evaluate-mandate across product scenarios
"""

import json
import urllib.request
import urllib.error


def make_request(url: str, method: str = "GET", payload: dict = None, timeout: int = 5):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_nach_service_e2e(base_url=None):
    if base_url is None:
        # Check host.docker.internal first when running in Docker
        base_url = "http://host.docker.internal:3007"
        try:
            req = urllib.request.Request(f"{base_url}/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                pass
        except Exception:
            base_url = "http://localhost:3007"

    print("=" * 70)
    print(f"E2E Test: NACH Mandate Recovery Service ({base_url})")
    print("=" * 70)

    # 1. Healthcheck
    health_url = f"{base_url}/health"
    try:
        health = make_request(health_url)
        assert health.get("status") == "online"
        assert health.get("service") == "nach-recovery-service"
        print(f"  ✅ PASS: /health -> Status: {health.get('status')}, Service: {health.get('service')}")
    except Exception as e:
        print(f"  ❌ FAIL: /health ({e})")
        return False

    # 2. Metrics Telemetry
    metrics_url = f"{base_url}/api/v1/nach-metrics"
    try:
        metrics = make_request(metrics_url)
        assert "total_mandates_evaluated" in metrics
        assert "governor_pre_emptions" in metrics
        assert "bank_retry_fees_saved_inr" in metrics
        assert "revenue_recovered_inr" in metrics
        print(f"  ✅ PASS: /api/v1/nach-metrics")
        print(f"     Total Evaluated:        {metrics['total_mandates_evaluated']}")
        print(f"     Governor Pre-Emptions:  {metrics['governor_pre_emptions']}")
        print(f"     Bank Fees Saved (INR):  ₹{metrics['bank_retry_fees_saved_inr']:,.2f}")
        print(f"     Revenue Recovered (INR): ₹{metrics['revenue_recovered_inr']:,.2f}")
    except Exception as e:
        print(f"  ❌ FAIL: /api/v1/nach-metrics ({e})")
        return False

    # 3. Synchronous Mandate Evaluations
    eval_url = f"{base_url}/api/v1/evaluate-mandate"

    cases = [
        {
            "name": "SIP Pre-Emptive Escalation (AMC 3-Failure Guard)",
            "payload": {
                "transaction_id": "e2e-sip-01",
                "payment_rail": "nach",
                "product_type": "sip",
                "mandate_value": 7500.0,
                "cause": "insufficient_funds",
                "consecutive_failure_count": 2,
            },
            "expected_action": "sip_cancellation_risk_escalate",
            "expected_urgency": "elevated",
            "expected_channel": "sms",
        },
        {
            "name": "EMI Credit Risk Escalation (Day 28 Guard -> WhatsApp)",
            "payload": {
                "transaction_id": "e2e-emi-01",
                "payment_rail": "nach",
                "product_type": "loan_emi",
                "mandate_value": 18500.0,
                "cause": "insufficient_funds",
                "consecutive_failure_count": 1,
                "days_since_due_date": 28,
            },
            "expected_action": "credit_score_risk_escalate",
            "expected_urgency": "critical",
            "expected_channel": "whatsapp",
        },
        {
            "name": "Permanent Mandate Failure Hard-Stop",
            "payload": {
                "transaction_id": "e2e-perm-01",
                "payment_rail": "nach",
                "product_type": "loan_emi",
                "mandate_value": 12000.0,
                "cause": "mandate_expired",
                "consecutive_failure_count": 1,
                "days_since_due_date": 10,
            },
            "expected_action": "nach_do_not_retry",
            "expected_urgency": "critical",
            "expected_channel": "whatsapp",
        },
    ]

    for tc in cases:
        try:
            res = make_request(eval_url, method="POST", payload=tc["payload"])
            assert res.get("action") == tc["expected_action"], (
                f"Action mismatch: got {res.get('action')}, want {tc['expected_action']}"
            )
            assert res.get("urgency_tier") == tc["expected_urgency"], (
                f"Urgency mismatch: got {res.get('urgency_tier')}, want {tc['expected_urgency']}"
            )
            assert res.get("recommended_channel") == tc["expected_channel"], (
                f"Channel mismatch: got {res.get('recommended_channel')}, want {tc['expected_channel']}"
            )
            print(f"  ✅ PASS: {tc['name']}")
            print(f"     Action:  {res.get('action')}")
            print(f"     Channel: {res.get('recommended_channel').upper()} (Tier: {res.get('urgency_tier')})")
            print(f"     Reason:  {res.get('reasoning')[:75]}...")
        except Exception as e:
            print(f"  ❌ FAIL: {tc['name']} ({e})")
            return False

    print("=" * 70)
    print("ALL NACH RECOVERY SERVICE E2E TESTS PASSED")
    print("=" * 70)
    return True


if __name__ == "__main__":
    test_nach_service_e2e()
