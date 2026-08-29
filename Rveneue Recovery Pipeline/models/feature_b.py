import os
import joblib
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from data_generator import DataGenerator
from config import MODELS_DIR
from schemas import RetryInput, RetryOutput, RetryAlternative, CauseEnum

class FeatureBModel:
    def __init__(self):
        self.model_path = os.path.join(MODELS_DIR, "feature_b.joblib")
        self.cause_map = {
            CauseEnum.soft_decline: 0,
            CauseEnum.hard_decline: 1,
            CauseEnum.gateway_fault: 2,
            CauseEnum.fraud_filter_block: 3,
            CauseEnum.notification_compliance_block: 4
        }
        self.pm_map = {
            "upi": 0,
            "card": 1,
            "netbanking": 2,
            "wallet": 3
        }
        self.model = self._load_or_train()

    def _load_or_train(self):
        if os.path.exists(self.model_path):
            return joblib.load(self.model_path)
        return self.train_model()

    def train_model(self):
        df = DataGenerator.generate_retry_data()
        X = df[["hour_of_day", "day_of_month", "failure_cause_encoded", "payment_method_encoded", "retry_count", "time_since_failure_mins"]]
        y = df["retry_success"]
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X, y)
        joblib.dump(clf, self.model_path)
        return clf

    def predict(self, input_data: RetryInput) -> RetryOutput:
        now = datetime.now()
        candidates = [2, 10, 60, 720, 1440, 2880]
        cause_encoded = self.cause_map.get(input_data.failure_cause, 0)
        pm_encoded = self.pm_map.get(input_data.payment_method.lower(), 0)
        
        alternatives = []
        for mins in candidates:
            future_time = now + timedelta(minutes=mins)
            features = [[
                future_time.hour,
                future_time.day,
                cause_encoded,
                pm_encoded,
                1,
                mins
            ]]
            prob = self.model.predict_proba(features)[0][1]
            alternatives.append(RetryAlternative(window=future_time, probability=float(prob)))
            
        alternatives.sort(key=lambda x: x.probability, reverse=True)
        return RetryOutput(
            recommended_retry_window=alternatives[0].window,
            predicted_success_probability=alternatives[0].probability,
            ranked_alternative_windows=alternatives[1:]
        )