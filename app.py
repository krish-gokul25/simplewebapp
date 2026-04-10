"""
app.py — CC Underwriting Inference API
Azure Web App: uvicorn app:app --host 0.0.0.0 --port 8000
"""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import mlflow.sklearn
import numpy as np
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
MODEL_DIR = Path("model")

SCORE_OFFSET = 600
SCORE_FACTOR = 72
APPROVAL_THRESHOLD = 0.5
EPSILON = 1e-8

RISK_BANDS: list[tuple[float, str]] = [
    (500, "Very High Risk"),
    (560, "High Risk"),
    (620, "Medium Risk"),
    (680, "Low Risk"),
    (740, "Very Low Risk"),
]


# ── Model state ───────────────────────────────────────────────────────────────
class ModelRegistry:
    model = None
    features: list[str] = []
    metrics: dict = {}
    scaler_mean: np.ndarray = None
    scaler_scale: np.ndarray = None

    @classmethod
    def load(cls) -> None:
        log.info("Loading model artifacts from '%s'...", MODEL_DIR)

        cls.model = mlflow.sklearn.load_model(MODEL_DIR / "rf")
        cls.features = json.loads((MODEL_DIR / "features.json").read_text())
        cls.metrics = json.loads((MODEL_DIR / "metrics.json").read_text())

        scaler = json.loads((MODEL_DIR / "scaler.json").read_text())
        cls.scaler_mean = np.array(scaler["mean"])
        cls.scaler_scale = np.array(scaler["scale"])

        log.info("Model loaded — %d features.", len(cls.features))


@asynccontextmanager
async def lifespan(app: FastAPI):
    ModelRegistry.load()
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="CC Underwriting API", version="1.0", lifespan=lifespan)


# ── Schemas ───────────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    applicant_id: str | None = None
    features: Annotated[dict[str, float], Field(min_length=1)]

    @field_validator("features")
    @classmethod
    def no_nan_inf(cls, v: dict) -> dict:
        bad = [k for k, val in v.items() if not np.isfinite(val)]
        if bad:
            raise ValueError(f"Non-finite values for features: {bad}")
        return v


class PredictResponse(BaseModel):
    applicant_id: str | None
    decision: str
    approval_prob: float
    scorecard_score: float
    risk_band: str


class ModelInfoResponse(BaseModel):
    feature_count: int
    metrics: dict


# ── Scoring helpers ───────────────────────────────────────────────────────────
def to_scorecard(prob: float) -> float:
    """Convert approval probability to a FICO-style scorecard score."""
    odds = (1 - prob + EPSILON) / (prob + EPSILON)
    return round(SCORE_OFFSET + SCORE_FACTOR * np.log(odds), 1)


def to_risk_band(score: float) -> str:
    for threshold, label in RISK_BANDS:
        if score < threshold:
            return label
    return "Excellent"


def build_feature_vector(features: dict[str, float]) -> np.ndarray:
    """Align incoming features to the model's expected order, defaulting unknowns to 0."""
    return np.array(
        [features.get(f, 0.0) for f in ModelRegistry.features],
        dtype=np.float64,
    )


def scale(vector: np.ndarray) -> np.ndarray:
    return (vector - ModelRegistry.scaler_mean) / ModelRegistry.scaler_scale


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/model", response_model=ModelInfoResponse, tags=["ops"])
def model_info() -> ModelInfoResponse:
    return ModelInfoResponse(
        feature_count=len(ModelRegistry.features),
        metrics=ModelRegistry.metrics,
    )


@app.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    tags=["inference"],
)
def predict(req: PredictRequest) -> PredictResponse:
    try:
        vector = build_feature_vector(req.features)
        prob = float(ModelRegistry.model.predict_proba(scale(vector).reshape(1, -1))[0][1])
    except Exception as exc:
        log.exception("Inference failed for applicant '%s'", req.applicant_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    sc = to_scorecard(prob)

    log.info(
        "applicant=%s prob=%.4f score=%.1f decision=%s",
        req.applicant_id,
        prob,
        sc,
        "Approved" if prob >= APPROVAL_THRESHOLD else "Declined",
    )

    return PredictResponse(
        applicant_id=req.applicant_id,
        decision="Approved" if prob >= APPROVAL_THRESHOLD else "Declined",
        approval_prob=round(prob, 4),
        scorecard_score=sc,
        risk_band=to_risk_band(sc),
    )