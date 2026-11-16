"""Research-only category-aware calibrator layered over the SHIPPED XLM-R probabilities.

The original RoBERTa still reads unchanged raw review text. Category context
is learned by a light linear model, never added to the ONNX encoder input.
This module has NO activation mode: all outputs are shadow-only audit data.
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

import numpy as np
from scipy.sparse import csr_matrix, hstack

from .product_category import classify_listing, group_of

REVISION = "roberta-category-calibrator-v1-research"
ENV = "DEFAKETIVE_CATEGORY_SENTIMENT_ADAPTER"
SHADOW_ENV = "DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW"
CLASSES = ("negative", "neutral", "positive")
CUES = {
    "thin": r"\b(?:thin|manipis|nipis)\b",
    "light": r"\b(?:lightweight|magaan|light)\b",
    "heavy": r"\b(?:heavy|mabigat)\b",
    "hot": r"\b(?:hot|mainit|init|overheat\w*)\b",
    "cold": r"\b(?:cold|cool|malamig)\b",
    "soft": r"\b(?:soft|malambot)\b",
    "tight": r"\b(?:tight|masikip)\b",
    "loose": r"\b(?:loose|maluwag)\b",
    "small": r"\b(?:small|maliit)\b",
    "big": r"\b(?:big|malaki|large)\b",
    "fast": r"\b(?:fast|mabilis)\b",
    "slow": r"\b(?:slow|mabagal)\b",
    "weak": r"\b(?:weak|mahina)\b",
    "strong": r"\b(?:strong|malakas)\b",
    "smell": r"\b(?:smell\w*|amoy|bango|mabango)\b",
    "noisy": r"\b(?:noisy|maingay|ingay)\b",
    "cheap": r"\b(?:cheap|mura|mumurahin)\b",
    "durable": r"\b(?:durable|matibay|durability)\b",
}
COMPILED = {k: re.compile(v, re.I) for k, v in CUES.items()}


@lru_cache(maxsize=4096)
def title_category(title: str) -> tuple[str, str]:
    category = classify_listing({"name": title})
    return category, group_of(category)


def context_features(text: str, title: str, supported_categories: set[str] | None = None) -> dict[str, float]:
    """Category/group x review-word context; never trust a supplied category."""
    cat, group = title_category(str(title or ""))
    if cat == "other":
        return {}
    supported = cat if supported_categories is None or cat in supported_categories else "rare"
    feats = {"group=" + group: 1., "category=" + supported: 1.}
    for name, pattern in COMPILED.items():
        if pattern.search(str(text or "")):
            feats["group=" + group + ":cue=" + name] = 1.
    return feats


def model_features(texts: list[str], stars: list[Any], probs: np.ndarray, titles: list[str],
                   word: Any, char: Any, context_vectorizer: Any,
                   supported_categories: set[str] | None = None) -> Any:
    if probs.shape != (len(texts), 3) or len(stars) != len(texts) or len(titles) != len(texts):
        raise ValueError("model feature dimensions do not match")
    if not np.isfinite(probs).all() or (probs < 0).any() or (probs > 1).any():
        raise ValueError("invalid RoBERTa probabilities")
    onehot = []
    for raw in stars:
        try:
            n = int(float(raw))
        except (ValueError, TypeError, OverflowError):
            n = 0
        onehot.append([float(n == i) for i in range(1, 6)])
    dense = np.column_stack((probs, np.asarray(onehot, dtype=float)))
    extras = [context_features(t, title, supported_categories)
              for t, title in zip(texts, titles)]
    return hstack((word.transform(texts), char.transform(texts),
                   csr_matrix(dense), context_vectorizer.transform(extras)),
                  format="csr")


def validate_manifest(path: str | Path, expected_encoder_sha256: str) -> dict[str, Any]:
    """Reject wrong base model, unaudited artifact, or false qualification."""
    candidate = Path(path).resolve()
    manifest_path = candidate.with_suffix(".json")
    if not candidate.is_file() or not manifest_path.is_file():
        raise ValueError("candidate and manifest must both exist")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("stage") != "research_shadow"
            or manifest.get("qualified_for_integration") is not False
            or manifest.get("revision") != REVISION):
        raise ValueError("not a research-only shadow artifact")
    if manifest.get("base_encoder_sha256") != expected_encoder_sha256:
        raise ValueError("RoBERTa encoder hash mismatch")
    with candidate.open("rb") as fh:
        digest = hashlib.file_digest(fh, "sha256").hexdigest()
    if digest != manifest.get("artifact_sha256"):
        raise ValueError("artifact SHA256 mismatch")
    return manifest


class CategoryAdapter:
    def __init__(self, artifact_path: str | Path, encoder_sha256: str):
        self.manifest = validate_manifest(artifact_path, encoder_sha256)
        # joblib is pickle: ONLY load trusted locally audited artifacts.
        import joblib
        bundle = joblib.load(artifact_path)
        if bundle.get("revision") != REVISION or tuple(bundle.get("classes", ())) != CLASSES:
            raise ValueError("unexpected category adapter format")
        self.word = bundle["word"]
        self.char = bundle["char"]
        self.context_vectorizer = bundle["context_vectorizer"]
        self.supported_categories = set(bundle["supported_categories"])
        self.classifier = bundle["classifier"]

    def predict(self, text: str, rating: Any, probabilities: Mapping[str, Any], title: str) -> dict[str, Any]:
        category, group = title_category(title)
        if category == "other" or group == "other":
            raise ValueError("unknown title category: use original RoBERTa")
        p = np.array([[float(probabilities[x]) for x in CLASSES]], dtype=float)
        features = model_features([text], [rating], p, [title],
                                  self.word, self.char, self.context_vectorizer,
                                  self.supported_categories)
        values = self.classifier.predict_proba(features)[0]
        found = {str(k): float(v) for k, v in zip(self.classifier.classes_, values)}
        label = max(CLASSES, key=lambda k: found.get(k, 0.))
        return {"revision": REVISION, "mode": "shadow", "product_category": category,
                "product_group": group, "candidate_label": label,
                "candidate_probabilities": {k: round(found.get(k, 0.), 6) for k in CLASSES},
                "used_for_decision": False}


_CACHE: dict[tuple[str, str], CategoryAdapter] = {}


def shadow(text: str, rating: Any, probabilities: Mapping[str, Any] | None,
           listing: Mapping[str, Any] | None, deployed_label: str,
           encoder_sha256: str | None) -> dict[str, Any] | None:
    """Fail closed: no label returned to production paths, ever."""
    if os.environ.get(SHADOW_ENV, "").strip().lower() not in {"1", "true", "yes", "shadow"}:
        return None
    path = os.environ.get(ENV, "").strip()
    if not path or not listing or not probabilities or not encoder_sha256 or deployed_label not in CLASSES:
        return None
    key = (path, encoder_sha256)
    try:
        if key not in _CACHE:
            _CACHE[key] = CategoryAdapter(path, encoder_sha256)
        guess = _CACHE[key].predict(str(text or ""), rating, probabilities, str(listing.get("name") or ""))
    except (OSError, ValueError, KeyError, TypeError, ImportError, AttributeError):
        return None
    guess["deployed_label"] = deployed_label
    guess["disagrees"] = guess["candidate_label"] != deployed_label
    return guess
