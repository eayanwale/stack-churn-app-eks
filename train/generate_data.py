"""Generate a synthetic but realistic Telco-style customer-churn dataset.

Churn is driven by well-known signals (month-to-month contracts, fibre,
electronic-check payment, short tenure, no tech support/security, high
monthly charges) so a model trained on it behaves sensibly in the demo.

Usage:  python train/generate_data.py --rows 6000 --out train/churn_train.csv
"""
import argparse
import numpy as np
import pandas as pd


def generate(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    def pick(choices, p=None):
        return rng.choice(choices, size=n, p=p)

    gender = pick(["Female", "Male"])
    senior = rng.binomial(1, 0.16, n)
    partner = pick(["No", "Yes"], [0.52, 0.48])
    dependents = pick(["No", "Yes"], [0.70, 0.30])
    tenure = rng.integers(0, 73, n)
    phone = pick(["No", "Yes"], [0.10, 0.90])
    internet = pick(["DSL", "Fiber optic", "No"], [0.34, 0.44, 0.22])

    def dep_service(prob_yes):
        out = []
        for net in internet:
            if net == "No":
                out.append("No internet service")
            else:
                out.append("Yes" if rng.random() < prob_yes else "No")
        return np.array(out)

    online_sec = dep_service(0.40)
    tech_sup = dep_service(0.40)
    stream_tv = dep_service(0.50)
    contract = pick(["Month-to-month", "One year", "Two year"], [0.55, 0.21, 0.24])
    paperless = pick(["No", "Yes"], [0.41, 0.59])
    payment = pick(
        ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"],
        [0.34, 0.23, 0.22, 0.21],
    )

    # monthly charges depend on services
    base = np.where(internet == "Fiber optic", 74.0, np.where(internet == "DSL", 48.0, 20.0))
    base = base + (online_sec == "Yes") * 6 + (tech_sup == "Yes") * 6 + (stream_tv == "Yes") * 11
    monthly = np.round(np.clip(base + rng.normal(0, 6, n), 18.25, 120.0), 2)
    total = np.round(np.clip(monthly * np.maximum(tenure, 0) * rng.uniform(0.97, 1.03, n), 0, None), 2)

    # ---- churn logit (higher = more likely to churn) ----
    z = -1.35
    z += np.where(contract == "Month-to-month", 1.15, np.where(contract == "One year", -0.35, -1.05))
    z += np.where(internet == "Fiber optic", 0.55, np.where(internet == "DSL", -0.10, -0.55))
    z += (payment == "Electronic check") * 0.55
    z += (paperless == "Yes") * 0.25
    z += (senior == 1) * 0.30
    z += (partner == "Yes") * -0.25 + (dependents == "Yes") * -0.20
    z += (online_sec == "Yes") * -0.35 + (tech_sup == "Yes") * -0.35
    z += (tenure < 6) * 0.9 + (tenure.astype(float) >= 48) * -0.8 - (tenure / 72.0) * 0.6
    z += (monthly - 65) / 45.0 * 0.4
    prob = 1 / (1 + np.exp(-z))
    churn = np.where(rng.random(n) < prob, "Yes", "No")

    df = pd.DataFrame({
        "gender": gender, "SeniorCitizen": senior, "Partner": partner, "Dependents": dependents,
        "tenure": tenure, "PhoneService": phone, "InternetService": internet,
        "OnlineSecurity": online_sec, "TechSupport": tech_sup, "StreamingTV": stream_tv,
        "Contract": contract, "PaperlessBilling": paperless, "PaymentMethod": payment,
        "MonthlyCharges": monthly, "TotalCharges": total, "Churn": churn,
    })
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="train/churn_train.csv")
    a = ap.parse_args()
    df = generate(a.rows, a.seed)
    df.to_csv(a.out, index=False)
    print(f"wrote {a.out}  rows={len(df)}  churn_rate={(df.Churn=='Yes').mean():.1%}")
