"""Train the customer-churn model and save it for the app / SageMaker.

Produces:
  model/churn_model.joblib   a self-contained sklearn Pipeline
                             (preprocessing + classifier)
  model/model_metadata.json  feature schema, metrics and model info

Usage:  python train/train_model.py
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# make `app` importable so we reuse the single feature schema
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.features import NUMERIC_FEATURES, CATEGORICAL_FEATURES, FEATURE_ORDER, TARGET
from train.generate_data import generate

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV = os.path.join(HERE, "churn_train.csv")
MODEL_DIR = os.path.join(ROOT, "model")


def load_data() -> pd.DataFrame:
    if os.path.exists(CSV):
        return pd.read_csv(CSV)
    return generate(6000)


def build_pipeline() -> Pipeline:
    cat_cols = list(CATEGORICAL_FEATURES.keys())
    # SeniorCitizen is numeric 0/1 in the frame -> treat as numeric passthrough
    cat_cols = [c for c in cat_cols if c != "SeniorCitizen"]
    num_cols = NUMERIC_FEATURES + ["SeniorCitizen"]

    pre = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ])
    clf = GradientBoostingClassifier(random_state=42)
    return Pipeline([("pre", pre), ("clf", clf)])


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = load_data()
    # normalise SeniorCitizen to 0/1 ints
    df["SeniorCitizen"] = (
        df["SeniorCitizen"].astype(str).str.lower().isin(["1", "yes", "true"]).astype(int)
    )
    X = df[FEATURE_ORDER].copy()
    y = (df[TARGET] == "Yes").astype(int)

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    pipe = build_pipeline()
    pipe.fit(X_tr, y_tr)

    proba = pipe.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    metrics = {
        "accuracy": round(float(accuracy_score(y_te, pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_te, proba)), 4),
        "n_train": int(len(X_tr)), "n_test": int(len(X_te)),
        "churn_rate": round(float(y.mean()), 4),
    }

    model_path = os.path.join(MODEL_DIR, "churn_model.joblib")
    joblib.dump(pipe, model_path)

    meta = {
        "model_type": "GradientBoostingClassifier",
        "framework": f"scikit-learn",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_order": FEATURE_ORDER,
        "numeric_features": NUMERIC_FEATURES + ["SeniorCitizen"],
        "categorical_features": {k: v for k, v in CATEGORICAL_FEATURES.items() if k != "SeniorCitizen"},
        "target": TARGET,
        "positive_label": "Yes (customer will churn)",
        "threshold": 0.5,
        "metrics": metrics,
    }
    with open(os.path.join(MODEL_DIR, "model_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"saved {model_path}")
    print("metrics:", json.dumps(metrics))


if __name__ == "__main__":
    main()
