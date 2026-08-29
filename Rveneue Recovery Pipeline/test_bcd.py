import sys
import os
import time
from sklearn.metrics import accuracy_score

# Add the pipeline directory to the path so we can import its modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from models.feature_b import FeatureBModel
from models.feature_c import FeatureCModel
from models.feature_d import FeatureDModel
from data_generator import DataGenerator

def test_feature_b():
    print("Testing Feature B (Retry Routing)...")
    model = FeatureBModel()
    df = DataGenerator.generate_retry_data(n_samples=500)
    
    # We will test the underlying model accuracy on a new batch of synthetic data
    X = df[["hour_of_day", "day_of_month", "failure_cause_encoded", "payment_method_encoded", "retry_count", "time_since_failure_mins"]]
    y = df["retry_success"]
    
    start_time = time.time()
    preds = model.model.predict(X)
    end_time = time.time()
    
    accuracy = accuracy_score(y, preds)
    print(f"Feature B Accuracy: {accuracy*100:.2f}%")
    print(f"Feature B Latency: {(end_time - start_time) / len(df):.6f} sec/prediction\n")

def test_feature_c():
    print("Testing Feature C (Dunning Optimization)...")
    model = FeatureCModel()
    df = DataGenerator.generate_dunning_data(n_samples=500)
    
    X = df[["channel_encoded", "time_since_failure_mins", "customer_tenure_months", "prior_payment_success_rate"]]
    y = df["customer_paid"]
    
    start_time = time.time()
    preds = model.model.predict(X)
    end_time = time.time()
    
    accuracy = accuracy_score(y, preds)
    print(f"Feature C Accuracy: {accuracy*100:.2f}%")
    print(f"Feature C Latency: {(end_time - start_time) / len(df):.6f} sec/prediction\n")

def test_feature_d():
    print("Testing Feature D (False Decline Detection)...")
    model = FeatureDModel()
    df = DataGenerator.generate_fraud_data(n_samples=500)
    
    X = df[["amount", "transaction_velocity", "is_known_device", "ip_risk_score", "merchant_category_encoded", "transaction_hour"]]
    y = df["is_fraud"]
    
    start_time = time.time()
    preds = model.model.predict(X)
    end_time = time.time()
    
    accuracy = accuracy_score(y, preds)
    print(f"Feature D Accuracy: {accuracy*100:.2f}%")
    print(f"Feature D Latency: {(end_time - start_time) / len(df):.6f} sec/prediction\n")

if __name__ == "__main__":
    print("="*50)
    print("PROTOTYPE (Features B, C, D) ACCURACY RESULTS")
    print("="*50)
    test_feature_b()
    test_feature_c()
    test_feature_d()
    print("="*50)
