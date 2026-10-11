"""Inference backends for the churn app.

Two interchangeable predictors, selected by the INFERENCE_MODE env var:

  INFERENCE_MODE=local   -> LocalPredictor    (loads model/churn_model.joblib)
  INFERENCE_MODE=aws     -> SageMakerPredictor (invokes a SageMaker endpoint)

Both expose the same interface:

    predictor.predict_one(record: dict) -> {"probability": float, "churn": bool}
    predictor.describe() -> dict   (shown in the UI footer / /health)
"""
from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd

from .features import FEATURE_ORDER, coerce_record

THRESHOLD = float(os.getenv("CHURN_THRESHOLD", "0.5"))


class LocalPredictor:
    """Runs the bundled scikit-learn pipeline in-process."""

    def __init__(self, model_path: str):
        import joblib
        self.model_path = model_path
        self.model = joblib.load(model_path)
        self.meta = {}
        meta_path = os.path.join(os.path.dirname(model_path), "model_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                self.meta = json.load(f)

    def predict_one(self, record: dict) -> dict:
        rec = coerce_record(record)
        X = pd.DataFrame([[rec[f] for f in FEATURE_ORDER]], columns=FEATURE_ORDER)
        proba = float(self.model.predict_proba(X)[:, 1][0])
        return {"probability": proba, "churn": proba >= THRESHOLD}

    def describe(self) -> dict:
        return {
            "mode": "local",
            "model_path": self.model_path,
            "model_type": self.meta.get("model_type", "sklearn Pipeline"),
            "metrics": self.meta.get("metrics", {}),
            "threshold": THRESHOLD,
        }


class SageMakerPredictor:
    """Invokes a deployed Amazon SageMaker endpoint via boto3.

    The endpoint is expected to accept application/json (a single record or a
    list of records) and return {"probability": ...} or a list of them. The
    handler in sagemaker/inference.py implements exactly that contract.
    """

    def __init__(self, endpoint_name: str, region: str | None = None):
        import boto3
        self.endpoint_name = endpoint_name
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.client = boto3.client("sagemaker-runtime", region_name=self.region)

    def predict_one(self, record: dict) -> dict:
        rec = coerce_record(record)
        resp = self.client.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType="application/json",
            Accept="application/json",
            Body=json.dumps(rec),
        )
        payload = json.loads(resp["Body"].read().decode("utf-8"))
        if isinstance(payload, list):
            payload = payload[0]
        proba = float(payload["probability"])
        return {"probability": proba, "churn": proba >= THRESHOLD}

    def describe(self) -> dict:
        return {
            "mode": "aws",
            "endpoint_name": self.endpoint_name,
            "region": self.region,
            "threshold": THRESHOLD,
        }


def get_predictor():
    """Factory driven purely by environment variables."""
    mode = os.getenv("INFERENCE_MODE", "local").strip().lower()
    if mode == "aws":
        endpoint = os.getenv("SAGEMAKER_ENDPOINT_NAME")
        if not endpoint:
            raise RuntimeError(
                "INFERENCE_MODE=aws requires SAGEMAKER_ENDPOINT_NAME to be set."
            )
        return SageMakerPredictor(endpoint, os.getenv("AWS_REGION"))
    # default: local
    default_model = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model", "churn_model.joblib"
    )
    model_path = os.getenv("MODEL_PATH", default_model)
    if not os.path.exists(model_path):
        raise RuntimeError(
            f"Local model not found at {model_path}. Run: python train/train_model.py"
        )
    return LocalPredictor(model_path)
