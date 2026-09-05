"""
End-to-End Causal Model Generation & Training
=============================================
1. Generates 50,000 synthetic sessions with continuous latents, correlated copula potential outcomes,
   and confounded historical logging policy (if not already present).
2. Trains S-Learner, T-Learner, Propensity Estimator, and RTO Model.
3. Evaluates policies against hidden Oracle test counterfactuals.
4. Exports all model artifacts to backend/inference-service and models/ml.
"""

import os
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scripts.generate_synthetic_dropoffs import generate_causal_dataset
from scripts.train_causal_recovery_pipeline import main as train_pipeline_main

def main():
    data_dir = os.path.join(repo_root, "data", "synthetic")
    train_file = os.path.join(data_dir, "observed", "train.csv")
    
    # 1. Generate synthetic data if needed
    if not os.path.exists(train_file):
        print(f"[generate_models] Synthetic training data not found at {train_file}.")
        print("[generate_models] Generating 50,000 causal synthetic sessions...")
        generate_causal_dataset(n_samples=50000, rho=0.85, seed=42, output_dir=data_dir)
    else:
        print(f"[generate_models] Found existing causal synthetic dataset at {train_file}.")
        
    # 2. Train Causal Models & Evaluate against Oracle
    print("[generate_models] Training Causal Models on synthetic observed data...")
    train_pipeline_main()
    print("[generate_models] All causal models generated and trained successfully!")

if __name__ == "__main__":
    main()
