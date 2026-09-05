import uuid
import json
import random
from datetime import datetime, timezone, timedelta
import os

def generate_checkout_session():
    session_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(5, 60))
    events = []
    
    # 1. Start Checkout
    events.append({
        "event_id": str(uuid.uuid4()),
        "session_id": session_id,
        "event_type": "checkout_started",
        "client_timestamp": start_time.isoformat(),
        "cart_value": round(random.uniform(500, 5000), 2)
    })
    
    # Scenario Selection
    scenario = random.choices(
        ["success", "app_switch_failure", "otp_delivery_delay", "genuine_abandonment", "vpa_validation_abort", "price_shock"],
        weights=[0.55, 0.15, 0.10, 0.10, 0.05, 0.05]
    )[0]
    
    current_time = start_time + timedelta(seconds=random.randint(5, 15))
    
    if scenario == "app_switch_failure":
        events.append({
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": "redirect_initiated",
            "client_timestamp": current_time.isoformat()
        })
        organic_p = 0.05
        intervention_p = 0.47
        
    elif scenario == "otp_delivery_delay":
        events.append({
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": "otp_sent",
            "client_timestamp": current_time.isoformat()
        })
        organic_p = 0.08
        intervention_p = 0.40
        
    elif scenario == "success":
        events.append({
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": "redirect_initiated",
            "client_timestamp": current_time.isoformat()
        })
        current_time += timedelta(seconds=random.randint(5, 20))
        events.append({
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": "redirect_returned",
            "client_timestamp": current_time.isoformat()
        })
        current_time += timedelta(seconds=random.randint(2, 5))
        events.append({
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": "payment_success",
            "client_timestamp": current_time.isoformat()
        })
        organic_p = 1.0
        intervention_p = 1.0
        
    elif scenario == "genuine_abandonment":
        events.append({
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": "payment_method_selected",
            "client_timestamp": current_time.isoformat()
        })
        organic_p = 0.01
        intervention_p = 0.05

    elif scenario == "vpa_validation_abort":
        events.append({
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": "vpa_validation_failed",
            "client_timestamp": current_time.isoformat()
        })
        organic_p = 0.02
        intervention_p = 0.20
        
    elif scenario == "price_shock":
        events.append({
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": "cart_breakdown_viewed",
            "client_timestamp": current_time.isoformat()
        })
        organic_p = 0.01
        intervention_p = 0.35 # High recovery if we offer a discount

    # Simulate network duplicates
    if random.random() < 0.1 and len(events) > 1:
        dup_event = events[-1].copy()
        events.append(dup_event) # Duplicate event_id
        
    # Shuffle slightly to simulate network out-of-order for nearby events
    if random.random() < 0.2 and len(events) > 2:
        idx = len(events) - 1
        events[idx], events[idx-1] = events[idx-1], events[idx]
        
    organic_outcome = random.random() < organic_p
    intervention_outcome = random.random() < intervention_p
    
    return {
        "session_id": session_id,
        "scenario": scenario,
        "organic_recovery_p": organic_p,
        "intervention_recovery_p": intervention_p,
        "organic_outcome": organic_outcome,
        "intervention_outcome": intervention_outcome,
        "events": events
    }

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "synthetic")
    os.makedirs(data_dir, exist_ok=True)
    sessions = [generate_checkout_session() for _ in range(1000)]
    output_path = os.path.join(data_dir, "dropoff_sessions.json")
    with open(output_path, "w") as f:
        json.dump(sessions, f, indent=2)
    print(f"Generated 1000 synthetic sessions in {output_path}")

if __name__ == "__main__":
    main()
