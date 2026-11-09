"""Learned heads on the shipped XLM-R encoder: sentiment, mixed and aspects.

Trained by scripts/train_review_heads.py on evaluation/enhanced_dataset_v1.
The heads read the encoder's mean last hidden layer plus its own probabilities,
so one ONNX run per review gives everything (no second model is loaded).

The default "xlmr" model uses ExtrasTransformerSentimentClassifier: the shipped
label unchanged, plus the mixed flag and aspects. The heads' own sentiment label
(HeadedTransformerSentimentClassifier) is served only when
DEFAKETIVE_SENTIMENT_MODEL=xlmr_heads: it beat the shipped model against AI
labels but not on the small human-labeled gold/held-out sets.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import numpy as np

from .transformer_sentiment import EMBEDDING_OUTPUT, TransformerSentimentClassifier, feature_text

HEADS_VERSION = "review-heads-1.0.0"
SENTIMENT_LABELS = ["negative", "neutral", "positive"]
ASPECTS = ("delivery", "packaging", "seller_service", "price", "quality", "functionality")
DEFAULT_HEADS_DIR = Path(__file__).resolve().parents[1] / "models" / "review_heads_v1"
# Lazada/Shopee auto-suggested praise: "Sleek design, Fast charging, Great value,"
TEMPLATE = re.compile(r"^([A-Z][^,]{3,60},\s*){2,}")


def encode(classifier: TransformerSentimentClassifier, text: str) -> tuple[np.ndarray, np.ndarray]:
    """One ONNX run: (768-d mean hidden state, base-model probabilities)."""
    text = str(text or "").strip()
    encoding = classifier.tokenizer.encode(text if classifier.wants_raw_text else feature_text(text))
    feeds = {"input_ids": np.array([encoding.ids], dtype=np.int64),
             "attention_mask": np.array([encoding.attention_mask], dtype=np.int64)}
    logits, hidden = classifier.session.run(["logits", EMBEDDING_OUTPUT], feeds)
    values = classifier._softmax(logits[0].astype(np.float64))
    order = [classifier.labels.index(label) for label in SENTIMENT_LABELS]
    return hidden[0].astype(np.float32).mean(axis=0), values[order].astype(np.float32)


def feature_vector(embedding: np.ndarray, probabilities: np.ndarray) -> np.ndarray:
    return np.concatenate([embedding, np.log(np.clip(probabilities, 1e-6, 1))]).astype(np.float32)


def is_template(text: Any) -> bool:
    return bool(TEMPLATE.match(str(text or "").strip()))


# Lazada's review form fields: "Battery Life:matagal Performance:good".
FIELD = re.compile(r"(?:^|(?<=[\s.,;!]))[^\w\s]?\s*([A-Z][A-Za-z]+(?: [A-Za-z]+){0,3}) ?:\s*")


def template_sentences(text: Any) -> str:
    """Rewrite form fields as sentences ('Battery Life: matagal.'); other text unchanged.

    Glued fields read as neutral fragments to the encoder; separating them was
    the best template handling in scripts/sentiment_boost_experiments.py.
    """
    text = str(text or "")
    if not FIELD.search(text):
        return text
    return FIELD.sub(lambda m: ". " + m.group(1) + ": ", text).lstrip(". ").strip()


def star_conflict(label: str | None, rating: Any) -> bool:
    """Text clearly positive with 1-2 stars, or clearly negative with 4-5."""
    try:
        stars = float(rating)
    except (TypeError, ValueError):
        return False
    return (label == "positive" and stars <= 2) or (label == "negative" and stars >= 4)


class ReviewHeads:
    def __init__(self, heads_dir: str | Path | None = None):
        import joblib

        self.heads_dir = Path(heads_dir) if heads_dir else DEFAULT_HEADS_DIR
        self.manifest = json.loads((self.heads_dir / "manifest.json").read_text(encoding="utf-8"))
        self.sentiment = joblib.load(self.heads_dir / "sentiment.joblib")
        mixed = joblib.load(self.heads_dir / "mixed.joblib")
        self.mixed, self.mixed_threshold = mixed["model"], float(mixed["threshold"])
        self.aspects = joblib.load(self.heads_dir / "aspects.joblib")
        self.version = f"{self.manifest['version']}-{self.manifest['files']['sentiment.joblib'][:8]}"
        self.qualified_for_integration = bool(self.manifest.get("qualified_for_integration"))

    def predict(self, features: np.ndarray) -> dict[str, Any]:
        row = features.reshape(1, -1)
        probabilities = dict(zip(self.sentiment.classes_, self.sentiment.predict_proba(row)[0]))
        label = max(probabilities, key=probabilities.get)
        mixed_probability = float(self.mixed.predict_proba(row)[0][list(self.mixed.classes_).index(True)])
        aspects = {}
        for aspect, heads in self.aspects.items():
            mention = float(heads["mention"].predict_proba(row)[0][list(heads["mention"].classes_).index(True)])
            if mention >= heads["threshold"]:
                polarity = heads["polarity"]
                scores = dict(zip(polarity.classes_, polarity.predict_proba(row)[0]))
                best = max(scores, key=scores.get)
                aspects[aspect] = {"label": str(best), "confidence": round(float(scores[best]), 4),
                                   "mention_probability": round(mention, 4)}
        return {
            "label": str(label),
            "confidence": round(float(probabilities[label]), 6),
            "probabilities": {str(k): round(float(v), 6) for k, v in probabilities.items()},
            "mixed": {"detected": mixed_probability >= self.mixed_threshold,
                      "probability": round(mixed_probability, 4), "threshold": self.mixed_threshold},
            "aspects": aspects,
        }


class HeadedTransformerSentimentClassifier(TransformerSentimentClassifier):
    """The shipped transformer with the learned heads deciding the label."""

    label_source = "xlmr_review_heads"

    def __init__(self, model_dir: str | Path | None = None, *, heads_dir: str | Path | None = None,
                 threads: int = 1):
        super().__init__(model_dir, threads=threads)
        if not self.has_embedding:
            raise RuntimeError("The review heads need the encoder's hidden_states output.")
        self.heads = ReviewHeads(heads_dir)
        self.base_model_version = self.model_version
        self.model_version = f"{self.base_model_version}+{self.heads.version}"

    def base_view(self) -> TransformerSentimentClassifier:
        """The plain fine-tuned classifier on the same ONNX session (no reload)."""
        view = object.__new__(TransformerSentimentClassifier)
        view.__dict__.update(self.__dict__)
        view.model_version = self.base_model_version
        return view

    def predict(self, text: str) -> dict[str, Any]:
        embedding, base = encode(self, text)
        result = self.heads.predict(feature_vector(embedding, base))
        result["base_probabilities"] = {label: round(float(v), 6) for label, v in zip(SENTIMENT_LABELS, base)}
        result["evidence"] = []
        return result


DEFAULT_BLEND_DIR = Path(__file__).resolve().parents[1] / "models" / "sentiment_blend_v1"


class BlendedTransformerSentimentClassifier(TransformerSentimentClassifier):
    """Shipped model blended with a human-label head, plus the review extras.

    label = argmax((1 - w) * shipped + w * head), both computed on the review
    with form fields rewritten as sentences. The head was trained only on
    human-labelled rows (FiReCS / SentiTaglish); w, C and the template style
    were tuned on human validation rows. Hazard checks keep reading the plain
    shipped model on raw text (base_view), so their calibration is unchanged.
    """

    label_source = "xlmr_blend"

    def __init__(self, model_dir: str | Path | None = None, *, blend_dir: str | Path | None = None,
                 heads_dir: str | Path | None = None, threads: int = 1):
        import joblib

        super().__init__(model_dir, threads=threads)
        if not self.has_embedding:
            raise RuntimeError("The blend needs the encoder's hidden_states output.")
        blend_dir = Path(blend_dir) if blend_dir else DEFAULT_BLEND_DIR
        self.blend_manifest = json.loads((blend_dir / "manifest.json").read_text(encoding="utf-8"))
        self.head = joblib.load(blend_dir / "head.joblib")
        self.weight = float(self.blend_manifest["weight"])
        self.order = [list(self.head.classes_).index(label) for label in SENTIMENT_LABELS]
        self.heads = ReviewHeads(heads_dir)
        self.extras_version = self.heads.version
        self.base_model_version = self.model_version
        blend_version = f"{self.blend_manifest['version']}-{self.blend_manifest['files']['head.joblib'][:8]}"
        self.model_version = f"{self.base_model_version}+{blend_version}"

    def base_view(self) -> TransformerSentimentClassifier:
        view = object.__new__(TransformerSentimentClassifier)
        view.__dict__.update(self.__dict__)
        view.model_version = self.base_model_version
        return view

    def predict(self, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        rewritten = template_sentences(raw)
        embedding, base = encode(self, rewritten)
        head = self.head.predict_proba(feature_vector(embedding, base).reshape(1, -1))[0][self.order]
        blended = (1 - self.weight) * base + self.weight * head
        index = int(blended.argmax())
        # The extras were trained on reviews as written.
        raw_embedding, raw_base = (embedding, base) if rewritten == raw else encode(self, raw)
        extras = self.heads.predict(feature_vector(raw_embedding, raw_base))
        return {
            "label": SENTIMENT_LABELS[index],
            "confidence": round(float(blended[index]), 6),
            "probabilities": {label: round(float(v), 6) for label, v in zip(SENTIMENT_LABELS, blended)},
            "base_probabilities": {label: round(float(v), 6) for label, v in zip(SENTIMENT_LABELS, raw_base)},
            "template_rewritten": rewritten != raw,
            "evidence": [],
            "mixed": extras["mixed"],
            "aspects": extras["aspects"],
            "extras_version": self.extras_version,
        }


class ExtrasTransformerSentimentClassifier(TransformerSentimentClassifier):
    """The shipped label, unchanged, plus the heads' mixed flag and aspects.

    The positive/negative/neutral answer is exactly the fine-tuned model's
    (same logits, same argmax), so verdicts and the reported 0.833 / 0.706
    figures still describe it. Only extra fields are added, which is why
    model_version stays the encoder's and the add-on is versioned separately.
    """

    def __init__(self, model_dir: str | Path | None = None, *, heads_dir: str | Path | None = None,
                 threads: int = 1):
        super().__init__(model_dir, threads=threads)
        if not self.has_embedding:
            raise RuntimeError("The review extras need the encoder's hidden_states output.")
        self.heads = ReviewHeads(heads_dir)
        self.extras_version = self.heads.version

    def base_view(self) -> TransformerSentimentClassifier:
        view = object.__new__(TransformerSentimentClassifier)
        view.__dict__.update(self.__dict__)
        return view

    def predict(self, text: str) -> dict[str, Any]:
        embedding, base = encode(self, text)
        index = int(base.argmax())
        extras = self.heads.predict(feature_vector(embedding, base))
        return {
            "label": SENTIMENT_LABELS[index],
            "confidence": round(float(base[index]), 6),
            "probabilities": {label: round(float(v), 6) for label, v in zip(SENTIMENT_LABELS, base)},
            "evidence": [],
            "mixed": extras["mixed"],
            "aspects": extras["aspects"],
            "extras_version": self.extras_version,
        }
