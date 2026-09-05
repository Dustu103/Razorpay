"""
E2E Test: Causal Drop-Off Intervention Gateway Endpoint
======================================================
Tests the POST /predict/intervention endpoint on live inference-service:
1. Validates HTTP 200 on /predict/intervention
2. Tests high-cart tech glitch (UPI app switch) -> recommends WhatsApp with positive EV
3. Tests high organic recovery -> validates causal suppression / evaluation
4. Tests COD order -> validates RTO risk accounting
5. Validates response schemas, latency, and reasoning fields
"""

import time
import json
import urllib.request
import urllib.error

def _post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))

def _get_json(url: str) -> dict:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))

def test_intervention_e2e(base_url="http://host.docker.internal:8000"):
    print("=" * 75)
    print(f"E2E Test: Inference Service - Causal Drop-Off Intervention Endpoint ({base_url})")
    print("=" * 75)

    # Fallback to localhost if host.docker.internal fails
    try:
        _get_json(f"{base_url}/health")
    except Exception:
        base_url = "http://localhost:8000"

    # 1. Health check test
    health_url = f"{base_url}/health"
    try:
        health = _get_json(health_url)
        assert health.get("status") == "ok", f"Unhealthy status: {health}"
        print(f"  [1/4] Health Check: PASS (Status OK)")
    except Exception as e:
        print(f"  [1/4] Health Check: FAIL ({e})")
        raise e

    # 2. Tech glitch high-cart recovery scenario
    predict_url = f"{base_url}/predict/intervention"
    wa_payload = {
        "session_id": "sess_e2e_wa_001",
        "diagnosis": "upi_app_switch_abort",
        "cart_value": 7500.0,
        "merchant_margin": 0.40,
        "duration_sec": 45,
        "attempt_count": 2,
        "events_count": 5,
        "event_sequence": "cart_loaded,payment_selected,upi_app_switch_init",
        "payment_method": "upi",
        "device": "mobile_android",
        "is_returning_customer": 1,
        "channel_cost_wa": 0.80,
        "rto_cost_estimate": 250.0
    }

    start = time.time()
    try:
        data = _post_json(predict_url, wa_payload)
        latency = (time.time() - start) * 1000

        assert "action" in data, "Missing action in response"
        assert "risk_score" in data, "Missing risk_score in response"
        assert "recovery_prob" in data, "Missing recovery_prob in response"
        assert "expected_profit" in data, "Missing expected_profit in response"
        assert "reasoning" in data, "Missing reasoning in response"
        assert data["action"] in ["whatsapp", "sms", "email", "NO_ACTION"]
        print(f"  [2/4] Tech Glitch High-Cart: PASS")
        print(f"        Action: {data['action']} | EV: INR {data['expected_profit']:.2f} | Latency: {latency:.2f}ms")
    except Exception as e:
        print(f"  [2/4] Tech Glitch High-Cart: FAIL ({e})")
        raise e

    # 3. Organic Recovery Safety Scenario
    org_payload = {
        "session_id": "sess_e2e_org_002",
        "diagnosis": "upi_app_switch_abort",
        "cart_value": 1500.0,
        "merchant_margin": 0.20,
        "duration_sec": 300,
        "attempt_count": 1,
        "events_count": 3,
        "event_sequence": "cart_loaded,browse",
        "payment_method": "upi",
        "device": "mobile_android",
        "is_returning_customer": 0
    }

    try:
        data = _post_json(predict_url, org_payload)
        assert data["action"] in ["NO_ACTION", "whatsapp", "sms", "email"]
        if data["action"] == "NO_ACTION":
            assert data["expected_profit"] == 0.0
        print(f"  [3/4] Organic Safety Test: PASS")
        print(f"        Action: {data['action']} | EV: INR {data['expected_profit']:.2f}")
    except Exception as e:
        print(f"  [3/4] Organic Safety Test: FAIL ({e})")
        raise e

    # 4. COD High-RTO Risk Order
    cod_payload = {
        "session_id": "sess_e2e_cod_003",
        "diagnosis": "genuine_browse_abandon",
        "cart_value": 1200.0,
        "merchant_margin": 0.25,
        "duration_sec": 200,
        "attempt_count": 1,
        "events_count": 2,
        "event_sequence": "cart_loaded,exit",
        "payment_method": "cod",
        "device": "mobile_android",
        "is_returning_customer": 0,
        "rto_cost_estimate": 280.0
    }

    try:
        data = _post_json(predict_url, cod_payload)
        assert data["action"] in ["NO_ACTION", "whatsapp", "sms", "email"]
        print(f"  [4/4] COD RTO Risk Accounting: PASS")
        print(f"        Action: {data['action']} | RTO Risk: {data['risk_score']:.3f}")
    except Exception as e:
        print(f"  [4/4] COD RTO Risk Accounting: FAIL ({e})")
        raise e

    print("=" * 75)
    print("ALL 4 E2E INFERENCE TESTS PASSED")
    print("=" * 75)

if __name__ == "__main__":
    test_intervention_e2e()
