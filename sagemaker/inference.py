"""SageMaker inference handler for the churn model.

Packaged into the model tarball and used by the SageMaker scikit-learn
serving container. Implements the JSON contract the app expects:

  request  (application/json):  a single record object OR a list of records
  response (application/json):  {"probability": p, "churn": bool}  (or a list)

The four functions below are the SageMaker serving hooks.
"""
import json
import os

import joblib
import pandas as pd

# Same field order the model was trained on.
FEATURE_ORDER = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "InternetService", "OnlineSecurity", "TechSupport",
    "StreamingTV", "Contract", "PaperlessBilling", "PaymentMethod",
    "MonthlyCharges", "TotalCharges",
]
NUMERIC = {"tenure", "MonthlyCharges", "TotalCharges"}
THRESHOLD = float(os.getenv("CHURN_THRESHOLD", "0.5"))


def _coerce(rec):
    out = {}
    for f in FEATURE_ORDER:
        v = rec.get(f)
        if f == "SeniorCitizen":
            out[f] = 1 if str(v).strip().lower() in ("1", "yes", "true") else 0
        elif f in NUMERIC:
            out[f] = float(v)
        else:
            out[f] = str(v).strip()
    return out


def model_fn(model_dir):
    """Load the model from the extracted tarball."""
    return joblib.load(os.path.join(model_dir, "churn_model.joblib"))


def input_fn(body, content_type="application/json"):
    if content_type != "application/json":
        raise ValueError(f"Unsupported content type: {content_type}")
    data = json.loads(body)
    records = data if isinstance(data, list) else [data]
    return pd.DataFrame([[_coerce(r)[f] for f in FEATURE_ORDER] for r in records],
                        columns=FEATURE_ORDER)


def predict_fn(df, model):
    proba = model.predict_proba(df)[:, 1]
    return [{"probability": float(p), "churn": bool(p >= THRESHOLD)} for p in proba]


def output_fn(prediction, accept="application/json"):
    payload = prediction[0] if len(prediction) == 1 else prediction
    return json.dumps(payload), "application/json"
