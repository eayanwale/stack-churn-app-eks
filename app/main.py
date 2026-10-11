"""STACK IT — Customer Churn Predictor (Flask app)."""
from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

from .features import (CATEGORICAL_FEATURES, DEFAULTS, FIELD_LABELS,
                       FEATURE_ORDER, NUMERIC_FEATURES, coerce_record)
from .inference import get_predictor


def create_app() -> Flask:
    app = Flask(__name__)
    # Predictor is built once at startup from env vars (local or aws).
    app.predictor = get_predictor()

    def ui_fields():
        """Shape the schema for the template."""
        fields = []
        for f in FEATURE_ORDER:
            item = {"name": f, "label": FIELD_LABELS.get(f, f), "default": DEFAULTS.get(f)}
            if f in NUMERIC_FEATURES:
                item["type"] = "number"
            else:
                item["type"] = "select"
                item["choices"] = CATEGORICAL_FEATURES.get(f, [])
            fields.append(item)
        return fields

    @app.get("/")
    def index():
        return render_template(
            "index.html", fields=ui_fields(), backend=app.predictor.describe(),
        )

    @app.post("/predict")
    def predict():
        record = {f: request.form.get(f, DEFAULTS.get(f)) for f in FEATURE_ORDER}
        result = app.predictor.predict_one(record)
        pct = round(result["probability"] * 100, 1)
        band = "high" if pct >= 60 else ("medium" if pct >= 35 else "low")
        return render_template(
            "result.html",
            result=result, pct=pct, band=band,
            record=coerce_record(record), labels=FIELD_LABELS,
            order=FEATURE_ORDER, backend=app.predictor.describe(),
        )

    @app.post("/api/predict")
    def api_predict():
        """JSON API. Body: a single record object, or {"records": [ ... ]}."""
        data = request.get_json(force=True, silent=True) or {}
        records = data.get("records") if isinstance(data, dict) and "records" in data else [data]
        out = []
        for r in records:
            res = app.predictor.predict_one(r)
            out.append({"probability": round(res["probability"], 6), "churn": bool(res["churn"])})
        return jsonify(out[0] if len(out) == 1 else {"predictions": out})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "backend": app.predictor.describe()})

    return app


# module-level app for gunicorn: `gunicorn wsgi:app`
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=True)
