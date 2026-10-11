"""Single source of truth for the customer-churn feature schema.

Used by the training script, the Flask form, the local model and the
SageMaker inference handler so every layer agrees on the same fields.
"""

# Numeric features (free-form numbers)
NUMERIC_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges"]

# Categorical features -> the allowed choices shown in the UI dropdowns
CATEGORICAL_FEATURES = {
    "gender": ["Female", "Male"],
    "SeniorCitizen": ["No", "Yes"],          # stored as 0/1 by the app
    "Partner": ["No", "Yes"],
    "Dependents": ["No", "Yes"],
    "PhoneService": ["No", "Yes"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    "OnlineSecurity": ["No", "Yes", "No internet service"],
    "TechSupport": ["No", "Yes", "No internet service"],
    "StreamingTV": ["No", "Yes", "No internet service"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["No", "Yes"],
    "PaymentMethod": [
        "Electronic check", "Mailed check",
        "Bank transfer (automatic)", "Credit card (automatic)",
    ],
}

# The order the model expects its columns in
FEATURE_ORDER = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "InternetService", "OnlineSecurity", "TechSupport",
    "StreamingTV", "Contract", "PaperlessBilling", "PaymentMethod",
    "MonthlyCharges", "TotalCharges",
]

TARGET = "Churn"

# Human-friendly labels + sensible form defaults for the UI
FIELD_LABELS = {
    "gender": "Gender", "SeniorCitizen": "Senior citizen", "Partner": "Has partner",
    "Dependents": "Has dependents", "tenure": "Tenure (months)",
    "PhoneService": "Phone service", "InternetService": "Internet service",
    "OnlineSecurity": "Online security", "TechSupport": "Tech support",
    "StreamingTV": "Streaming TV", "Contract": "Contract",
    "PaperlessBilling": "Paperless billing", "PaymentMethod": "Payment method",
    "MonthlyCharges": "Monthly charges ($)", "TotalCharges": "Total charges ($)",
}

DEFAULTS = {
    "gender": "Female", "SeniorCitizen": "No", "Partner": "No", "Dependents": "No",
    "tenure": 12, "PhoneService": "Yes", "InternetService": "Fiber optic",
    "OnlineSecurity": "No", "TechSupport": "No", "StreamingTV": "No",
    "Contract": "Month-to-month", "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check", "MonthlyCharges": 70.0, "TotalCharges": 840.0,
}


def coerce_record(raw: dict) -> dict:
    """Normalise one raw form/JSON record into typed model input.

    - SeniorCitizen 'Yes'/'No'/'1'/'0'/1/0 -> 0/1
    - numeric fields -> float
    - everything else passed through as a trimmed string
    """
    rec = {}
    for f in FEATURE_ORDER:
        v = raw.get(f, DEFAULTS.get(f))
        if f == "SeniorCitizen":
            rec[f] = 1 if str(v).strip().lower() in ("1", "yes", "true") else 0
        elif f in NUMERIC_FEATURES:
            try:
                rec[f] = float(v)
            except (TypeError, ValueError):
                rec[f] = float(DEFAULTS[f])
        else:
            rec[f] = str(v).strip()
    return rec
