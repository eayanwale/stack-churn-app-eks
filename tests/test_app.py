"""Basic smoke tests:  python -m pytest -q   (or run directly)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("INFERENCE_MODE", "local")

from app.main import create_app  # noqa: E402

app = create_app()
client = app.test_client()

HIGH_RISK = {
    "gender": "Female", "SeniorCitizen": "Yes", "Partner": "No", "Dependents": "No",
    "tenure": 1, "PhoneService": "Yes", "InternetService": "Fiber optic",
    "OnlineSecurity": "No", "TechSupport": "No", "StreamingTV": "Yes",
    "Contract": "Month-to-month", "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check", "MonthlyCharges": 95.0, "TotalCharges": 95.0,
}
LOW_RISK = {
    "gender": "Male", "SeniorCitizen": "No", "Partner": "Yes", "Dependents": "Yes",
    "tenure": 68, "PhoneService": "Yes", "InternetService": "DSL",
    "OnlineSecurity": "Yes", "TechSupport": "Yes", "StreamingTV": "No",
    "Contract": "Two year", "PaperlessBilling": "No",
    "PaymentMethod": "Bank transfer (automatic)", "MonthlyCharges": 55.0, "TotalCharges": 3740.0,
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_index():
    assert client.get("/").status_code == 200


def test_api_predict_range():
    for rec in (HIGH_RISK, LOW_RISK):
        p = client.post("/api/predict", json=rec).get_json()["probability"]
        assert 0.0 <= p <= 1.0


def test_high_risk_scores_above_low_risk():
    hi = client.post("/api/predict", json=HIGH_RISK).get_json()["probability"]
    lo = client.post("/api/predict", json=LOW_RISK).get_json()["probability"]
    assert hi > lo, f"expected high-risk ({hi}) > low-risk ({lo})"


if __name__ == "__main__":
    test_health(); test_index(); test_api_predict_range(); test_high_risk_scores_above_low_risk()
    print("all smoke tests passed")
