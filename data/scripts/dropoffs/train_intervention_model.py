"""
Causal Recovery Model Training Entry Point
==========================================
Wraps the causal recovery pipeline to train:
1. Feature Preprocessor
2. Propensity Estimator (pi_hat_0)
3. S-Learner with X x A interactions
4. T-Learner (separate models)
5. Calibrated Downside Risk / RTO Model
Evaluates policy regret against the hidden Oracle test world and exports production artifacts.
"""

import sys
import os

# Add repo root to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from data.scripts.dropoffs.train_causal_recovery_pipeline import main as train_causal_main

def main():
    print("[train_intervention_model] Starting Causal Recovery Model Training...")
    train_causal_main()

if __name__ == "__main__":
    main()
