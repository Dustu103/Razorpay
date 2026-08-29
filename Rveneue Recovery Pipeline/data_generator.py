import numpy as np
import pandas as pd

class DataGenerator:
    @staticmethod
    def generate_retry_data(n_samples=5000):
        np.random.seed(42)
        day_of_month = np.random.randint(1, 31, n_samples)
        hour_of_day = np.random.randint(0, 24, n_samples)
        failure_cause_encoded = np.random.randint(0, 5, n_samples)
        payment_method_encoded = np.random.randint(0, 4, n_samples)
        retry_count = np.random.randint(1, 6, n_samples)
        time_since_failure_mins = np.random.randint(1, 1440, n_samples)
        
        success_probabilities = []
        for i in range(n_samples):
            cause = failure_cause_encoded[i]
            day = day_of_month[i]
            count = retry_count[i]
            
            if cause == 1:
                prob = 0.0
            else:
                prob = 0.35
                if cause == 2:
                    prob = 0.65
                if day in [1, 2, 7, 8]:
                    prob += 0.20
                if count > 3:
                    prob -= 0.30
                prob = max(0.0, min(1.0, prob))
            success_probabilities.append(prob)
            
        retry_success = np.random.binomial(1, success_probabilities)
        return pd.DataFrame({
            "hour_of_day": hour_of_day,
            "day_of_month": day_of_month,
            "failure_cause_encoded": failure_cause_encoded,
            "payment_method_encoded": payment_method_encoded,
            "retry_count": retry_count,
            "time_since_failure_mins": time_since_failure_mins,
            "retry_success": retry_success
        })

    @staticmethod
    def generate_dunning_data(n_samples=2000):
        np.random.seed(42)
        channel_encoded = np.random.randint(0, 3, n_samples)
        time_since_failure_mins = np.random.randint(5, 2880, n_samples)
        customer_tenure_months = np.random.randint(1, 60, n_samples)
        prior_payment_success_rate = np.random.uniform(0.1, 1.0, n_samples)
        
        response_probabilities = []
        for i in range(n_samples):
            ch = channel_encoded[i]
            mins = time_since_failure_mins[i]
            rate = prior_payment_success_rate[i]
            
            if ch == 0:
                base = 0.65
            elif ch == 1:
                base = 0.25
            else:
                base = 0.15
                
            if mins <= 30:
                mult = 1.0
            elif mins <= 120:
                mult = 0.7
            elif mins <= 720:
                mult = 0.4
            else:
                mult = 0.2
                
            prob = base * mult
            if rate > 0.85:
                prob += 0.15
            prob = max(0.0, min(1.0, prob))
            response_probabilities.append(prob)
            
        customer_paid = np.random.binomial(1, response_probabilities)
        return pd.DataFrame({
            "channel_encoded": channel_encoded,
            "time_since_failure_mins": time_since_failure_mins,
            "customer_tenure_months": customer_tenure_months,
            "prior_payment_success_rate": prior_payment_success_rate,
            "customer_paid": customer_paid
        })

    @staticmethod
    def generate_fraud_data(n_samples=5000):
        np.random.seed(42)
        amount = np.random.exponential(1500, n_samples) + 10
        transaction_velocity = np.random.randint(1, 10, n_samples)
        is_known_device = np.random.binomial(1, 0.8, n_samples)
        ip_risk_score = np.random.uniform(0.0, 1.0, n_samples)
        merchant_category_encoded = np.random.randint(0, 5, n_samples)
        transaction_hour = np.random.randint(0, 24, n_samples)
        
        fraud_probabilities = []
        for i in range(n_samples):
            vel = transaction_velocity[i]
            amt = amount[i]
            device = is_known_device[i]
            risk = ip_risk_score[i]
            
            prob = 0.02
            if vel > 5 and amt > 5000:
                prob = 0.85
            if risk > 0.8 and device == 0:
                prob = 0.90
            prob = max(0.0, min(1.0, prob))
            fraud_probabilities.append(prob)
            
        is_fraud = np.random.binomial(1, fraud_probabilities)
        return pd.DataFrame({
            "amount": amount,
            "transaction_velocity": transaction_velocity,
            "is_known_device": is_known_device,
            "ip_risk_score": ip_risk_score,
            "merchant_category_encoded": merchant_category_encoded,
            "transaction_hour": transaction_hour,
            "is_fraud": is_fraud
        })