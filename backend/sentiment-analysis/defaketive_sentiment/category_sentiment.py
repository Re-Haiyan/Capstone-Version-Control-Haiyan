"""Research-only, category-aware sentiment *shadow* suggestions.

The production XLM-R sentiment classifier was trained on review text, not text
prefixed with categories. Therefore we do not alter its input, labels, model
version, calibration or the hazard model's sentiment gate.

When DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW=1, a few narrow review phrases are
interpreted in light of the title-derived product category and saved as audit
metadata in the analysis result. The candidate is NOT used for aggregation,
warnings, product recommendations or displayed conclusions.

Category accuracy, candidate rules and their value over the current model
must be tested on independent, product-disjoint, human-adjudicated labels
before considering any replacement of live sentiment predictions.
"""

from __future__ import annotations

import os
import re
from typing import Any, Mapping

from .product_category import classify_listing

ENV = "DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW"
REVISION = "category-sentiment-shadow-v1"
LABELS = frozenset({"positive", "neutral", "negative"})

# Deliberately narrow, illustrative candidates for a pilot. Each condition is
# tied to the words *actually used* in the review. This is not a product-wide
# sentiment classifier and its coverage may be low.
_THIN = r"(?:thin|manipis|nipis)"
_CLOTHING = r"(?:tela|fabric|material|cloth|shirt|damit|cotton|bedsheet)"
_POSITIVE_THIN = re.compile(
    r"\b" + _THIN + r"\b.{0,40}\b(?:ganda|maganda|nice|sleek|looks? good|love|beautiful)\b"
    r"|\b(?:ganda|maganda|nice|sleek|looks? good|love|beautiful)\b.{0,40}\b" + _THIN + r"\b",
    re.I,
)
_NEGATIVE_FABRIC = re.compile(
    r"\b(?:too|very|sobrang|napaka|napaka\s+)\s+" + _THIN + r"\b.{0,45}\b" + _CLOTHING + r"\b"
    r"|\b" + _CLOTHING + r"\b.{0,45}\b(?:too|very|sobrang|napaka|napaka\s+)\s+" + _THIN + r"\b",
    re.I,
)
_NEGATIVE_BATTERY_HEAT = re.compile(
    r"\b(?:overheating|overheat(?:s|ed|ing)?|sobrang\s+init|masyadong\s+mainit)\b",
    re.I,
)
# A denial cancels a proposed negative even if a phrase above matches:
# "not too thin", "hindi sobrang init", "no overheating".
_DENIALS = re.compile(
    r"\b(?:not|never|no|hindi|di|walang|wala)\b.{0,28}"
    r"\b(?:too\s+thin|very\s+thin|sobrang\s+(?:nipis|manipis|init)|overheat(?:ing|s|ed)?|masyadong\s+mainit)\b",
    re.I,
)


def enabled() -> bool:
    """Explicit opt-in only; 'on' does not exist because this is a shadow."""
    return os.environ.get(ENV, "").strip().lower() in {"1", "true", "yes", "shadow"}


def suggest(
    review: Any,
    listing: Mapping[str, Any] | None,
    deployed_label: str | None,
) -> dict[str, Any] | None:
    """Return an auditable candidate, *never* an authoritative label.

    A known category is derived from the product title by the same classifier
    used for hazard checks. Do not trust a user-supplied category parameter,
    description, or the contents of a review to choose a product category.
    """
    if not enabled() or not isinstance(listing, Mapping) or deployed_label not in LABELS:
        return None
    category = classify_listing({"name": str(listing.get("name") or "")})
    text = str(review or "").strip()
    if category == "other" or not text or len(text) > 5000:
        return None

    candidate: str | None = None
    match: re.Match[str] | None = None
    reason: str | None = None

    if category in {"phone", "laptop", "tablet"}:
        match = _POSITIVE_THIN.search(text)
        if match and not re.search(r"\b(?:not|hindi|di)\s+" + _THIN + r"\b", text, re.I):
            candidate, reason = "positive", "thin_device_praised"
    elif category in {"apparel", "home_textile"} and not _DENIALS.search(text):
        match = _NEGATIVE_FABRIC.search(text)
        if match:
            candidate, reason = "negative", "fabric_too_thin"
    elif category in {"battery_solar", "powerbank"} and not _DENIALS.search(text):
        match = _NEGATIVE_BATTERY_HEAT.search(text)
        if match:
            candidate, reason = "negative", "battery_heat_complaint"

    if candidate is None or match is None or reason is None:
        return None
    return {
        "revision": REVISION,
        "mode": "shadow",
        "product_category": category,
        "deployed_label": deployed_label,
        "candidate_label": candidate,
        "disagrees": candidate != deployed_label,
        "rule": reason,
        "matched_text": match.group(0)[:120],
        "used_for_decision": False,
    }
