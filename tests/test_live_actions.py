import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "backend", "inference-service"))

from app.models.intervention_model import InterventionModel, InterventionInput

def test_live_actions():
    csv_path = "data/dropoffs/observed/test.csv"
    if not os.path.exists(csv_path):
        csv_path = "data/synthetic/observed/test.csv"
    if not os.path.exists(csv_path):
        print("Test data not found.")
        return

    df_test = pd.read_csv(csv_path)
    model_dir = "models/ml" if os.path.exists("models/ml") else "/app/models/ml"
    model = InterventionModel(model_dir)

    found = {}
    for i in range(len(df_test)):
        row = df_test.iloc[i]
        inp = InterventionInput(
            session_id=row["session_id"],
            diagnosis=row["diagnosis"],
            cart_value=float(row["cart_value"]),
            duration_sec=int(row["duration_sec"]),
            attempt_count=int(row["attempt_count"]),
            events_count=int(row["events_count"]),
            payment_method=row["payment_method"],
            device=row["device"],
            is_returning_customer=int(row["is_returning_customer"])
        )
        out = model.predict(inp)
        act = out.action
        
        # Validate mathematical and schema invariants
        assert 0.0 <= out.recovery_prob <= 1.0, f"Invalid recovery prob: {out.recovery_prob}"
        assert 0.0 <= out.organic_recovery_prob <= 1.0, f"Invalid organic prob: {out.organic_recovery_prob}"
        assert 0.0 <= out.risk_score <= 1.0, f"Invalid risk score: {out.risk_score}"
        assert 0.0 <= out.rto_rate_organic <= 1.0, f"Invalid rto organic: {out.rto_rate_organic}"
        assert out.action in ["NO_ACTION", "whatsapp", "sms", "email"]
        if out.action == "NO_ACTION":
            assert out.expected_profit == 0.0
        else:
            assert out.expected_profit > 0.0
            
        if act not in found:
            found[act] = (inp, out)
        if len(found) == 4:
            break

    assert len(found) > 0, "No actions predicted"

    print("=" * 80)
    print("LIVE PRODUCTION TEST ACROSS ALL 4 ACTION RECOMMENDATIONS:")
    print("=" * 80)
    for act, (inp, out) in sorted(found.items()):
        print(f"Action: {act.upper()}")
        print(f"  Session:         {inp.session_id} | Diagnosis: {inp.diagnosis} | Cart: INR {inp.cart_value:,.0f} | Device: {inp.device}")
        print(f"  Probabilities:   Recovery={out.recovery_prob:.3f} (Organic={out.organic_recovery_prob:.3f}, Lift=+{out.incremental_lift:.3f})")
        print(f"  Expected Profit: INR {out.expected_profit:,.2f}")
        print(f"  RTO Risk:        r_a={out.risk_score:.3f} vs r_0={out.rto_rate_organic:.3f}")
        print(f"  Reasoning:       {out.reasoning}")
        if out.recovery_message:
            print(f"  Hinglish Msg:    \"{out.recovery_message}\"")
        print("-" * 80)

if __name__ == "__main__":
    test_live_actions()
