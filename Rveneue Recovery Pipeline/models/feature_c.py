import os
import joblib
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from data_generator import DataGenerator
from config import MODELS_DIR
from schemas import DunningInput, DunningOutput

class FeatureCModel:
    def __init__(self):
        self.model_path = os.path.join(MODELS_DIR, "feature_c.joblib")
        self.channel_map = {
            "whatsapp_upi_link": 0,
            "sms": 1,
            "email": 2
        }
        self.inv_channel_map = {v: k for k, v in self.channel_map.items()}
        self.model = self._load_or_train()

    def _load_or_train(self):
        if os.path.exists(self.model_path):
            return joblib.load(self.model_path)
        return self.train_model()

    def train_model(self):
        df = DataGenerator.generate_dunning_data()
        X = df[["channel_encoded", "time_since_failure_mins", "customer_tenure_months", "prior_payment_success_rate"]]
        y = df["customer_paid"]
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X, y)
        joblib.dump(clf, self.model_path)
        return clf

    def predict(self, input_data: DunningInput) -> DunningOutput:
        now = datetime.now()
        scenarios = [
            ("whatsapp_upi_link", 15),
            ("sms", 60),
            ("email", 120)
        ]
        
        best_channel = "whatsapp_upi_link"
        best_prob = 0.0
        best_time = now
        
        for ch, mins in scenarios:
            features = [[
                self.channel_map[ch],
                mins,
                input_data.customer_tenure_months,
                input_data.prior_payment_success_rate
            ]]
            prob = self.model.predict_proba(features)[0][1]
            if prob > best_prob:
                best_prob = prob
                best_channel = ch
                best_time = now + timedelta(minutes=mins)
                
        return DunningOutput(
            recommended_channel=best_channel,
            predicted_response_probability=float(best_prob),
            recommended_send_time=best_time
        )