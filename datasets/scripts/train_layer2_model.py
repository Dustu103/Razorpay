import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, accuracy_score
import joblib
import time
import os

def train_model():
    print("Loading dataset...")
    # Adjust path if running from a different directory
    csv_path = os.path.join(os.path.dirname(__file__), "..", "payment_failures", "razorpay_payment_failures_synthetic.csv")
    df = pd.read_csv(csv_path)
    
    print(f"Dataset loaded with {len(df)} rows.")
    
    # Features to use for training
    categorical_features = [
        'status_code', 'bank_response_code', 'npci_response_code', 
        'currency', 'card_network', 'card_country_code', 'issuer_bank', 
        'is_recurring_transaction', 'cardholder_auth_method'
    ]
    numeric_features = ['amount_paise', 'retry_count_so_far']
    
    # Target variable
    target = 'label_cause'
    
    # Handle missing values as string 'MISSING' for categories
    for col in categorical_features:
        df[col] = df[col].fillna('MISSING').astype(str)
        
    X = df[categorical_features + numeric_features]
    y = df[target]
    
    print("Splitting dataset into train and test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Create preprocessing pipelines
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='MISSING')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])

    # We use a Random Forest which is extremely fast and accurate for tabular data
    # n_estimators=50 and max_depth=15 keep it very lightweight
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=50, max_depth=15, n_jobs=-1, random_state=42))
    ])

    print("Training the Layer 2 model. This will only take a few seconds...")
    start_time = time.time()
    
    model_pipeline.fit(X_train, y_train)
    
    end_time = time.time()
    print(f"Training completed in {end_time - start_time:.2f} seconds!")
    
    # Evaluate the model
    print("Evaluating model...")
    y_pred = model_pipeline.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {acc * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save the model to the ml-service models directory
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "ml-service", "models")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "layer2_payment_failure_model.pkl")
    print(f"Saving model as pickle to {output_path} ...")
    joblib.dump(model_pipeline, output_path)
    
    print("Done! You can now load this .pkl file in your Go or Python backend.")

if __name__ == "__main__":
    train_model()
