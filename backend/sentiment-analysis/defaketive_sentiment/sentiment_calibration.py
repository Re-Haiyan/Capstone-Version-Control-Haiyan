"""Optional sentiment recalibration: reads the deployed model's three probabilities, the star rating and the review text.

Why. On the team's labels the deployed XLM-R sentiment model reads "neutral" poorly (neutral F1 about 0.2: most reviews the
team calls neutral, often 5-star feature lists or "ok lang", are called positive). A small logistic regression over the
model's probabilities, the stars and word+char TF-IDF of the text lifts macro F1 from about 0.57-0.61 to about 0.72 on
product-grouped cross-validation and on the held-out products (research/results/exp_sentiment.json).

It is NOT wired into the pipeline by default. Set DEFAKETIVE_SENTIMENT_CALIBRATOR to the artifact path to use it from
code that calls `load_default()`; without it nothing changes, and any problem loading it falls back to the model's own label.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

CLASSES = ("negative", "neutral", "positive")
ENV = "DEFAKETIVE_SENTIMENT_CALIBRATOR"


class SentimentCalibrator:
    def __init__(self, bundle: dict[str, Any]):
        self.word = bundle["word"]
        self.char = bundle["char"]
        self.classifier = bundle["classifier"]
        self.classes = tuple(bundle["classes"])

    @classmethod
    def load(cls, path: str | Path) -> "SentimentCalibrator":
        import joblib

        return cls(joblib.load(path))

    def predict(self, text: str, stars: int, probabilities: dict[str, float] | list[float]) -> tuple[str, dict[str, float]]:
        from scipy.sparse import csr_matrix, hstack

        probs = [probabilities[c] for c in CLASSES] if isinstance(probabilities, dict) else list(probabilities)
        try:
            star = int(stars)
        except (TypeError, ValueError):
            star = 0  # no rating: every star indicator is 0
        dense = np.array([probs + [1.0 if star == s else 0.0 for s in range(1, 6)]], dtype=float)
        features = hstack([self.word.transform([text]), self.char.transform([text]), csr_matrix(dense)]).tocsr()
        out = self.classifier.predict_proba(features)[0]
        scores = {c: float(p) for c, p in zip(self.classes, out)}
        return max(scores, key=scores.get), scores


MODE_ENV = "DEFAKETIVE_SENTIMENT_CALIBRATOR_MODE"
_LOADED: dict[str, SentimentCalibrator | None] = {}


def load_default() -> SentimentCalibrator | None:
    """The calibrator named by the environment, or None (the default, and on any problem)."""
    path = os.environ.get(ENV, "").strip()
    if not path or not Path(path).is_file():
        return None
    if path not in _LOADED:
        try:
            _LOADED[path] = SentimentCalibrator.load(path)
        except Exception:  # noqa: BLE001 - a bad artifact must never break a scan
            _LOADED[path] = None
    return _LOADED[path]


def mode() -> str:
    """"shadow" (default when a calibrator is configured): record the calibrated sentiment beside the model's, change nothing;
    "on": the calibrated label replaces the model's. With no calibrator configured, nothing happens in either mode."""
    return "on" if os.environ.get(MODE_ENV, "shadow").strip().lower() == "on" else "shadow"


def calibrated_sentiment(text: str, stars: Any, probabilities: dict[str, float] | None) -> dict[str, Any] | None:
    """{"mode", "calibrated": {"label", "probabilities"}} or None (not configured, no probabilities, or any problem)."""
    calibrator = load_default()
    if calibrator is None or not probabilities or any(c not in probabilities for c in CLASSES):
        return None
    try:
        label, scores = calibrator.predict(text, stars, probabilities)
    except Exception:  # noqa: BLE001
        return None
    return {"mode": mode(), "calibrated": {"label": label, "probabilities": {k: round(v, 6) for k, v in scores.items()}}}
