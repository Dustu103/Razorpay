"""
E2E Test: Drop-Off Recovery Service
===================================
Tests dropoff-service HTTP API and worker telemetry:
1. Tests GET /api/v1/dropoff-metrics on port 3002
2. Validates metrics structure (active_sessions, interventions_sent, revenue_recovered)
"""

import json
import urllib.request
import urllib.error

def test_dropoff_metrics(base_url="http://host.docker.internal:3002"):
    print("=" * 65)
    print(f"E2E Test: Drop-Off Recovery Service API ({base_url})")
    print("=" * 65)

    # Fallback to localhost if host.docker.internal fails
    url = f"{base_url}/api/v1/dropoff-metrics"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        url = "http://localhost:3002/api/v1/dropoff-metrics"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

    assert "active_sessions" in data, f"Missing active_sessions: {data}"
    assert "interventions_sent" in data, f"Missing interventions_sent: {data}"
    assert "revenue_recovered" in data, f"Missing revenue_recovered: {data}"

    print(f"  Status: 200 OK")
    print(f"  Active Sessions:     {data['active_sessions']}")
    print(f"  Interventions Sent:  {data['interventions_sent']}")
    print(f"  Revenue Recovered:   INR {data['revenue_recovered']}")
    print("=" * 65)
    print("DROPOFF SERVICE E2E TEST PASSED")
    print("=" * 65)

if __name__ == "__main__":
    test_dropoff_metrics()
