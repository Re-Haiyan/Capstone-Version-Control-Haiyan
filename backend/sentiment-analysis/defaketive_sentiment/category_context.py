"""Category-context review check for the panel's five-stage flow.

Runs AFTER XLM-RoBERTa initial sentiment. All 49 recognized product categories
have explicit contextual phrase examples; unmatched, denied, ambiguous, mixed
and Other-category reviews abstain. This is an AUDITABLE INTERPRETATION,
not a validated sentiment classifier or an automatic label replacement.

Input review, title category, and initial model label are untrusted as user
content. The stage may never alter sentiment labels, hazard flags, verdicts,
the model input, or the stored report's model version.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Mapping

from .product_category import CATEGORIES, OTHER, classify_listing

REVISION = "category-context-v1"
_PROFILES_PATH = Path(__file__).with_name("category_context_profiles.json")
_LABELS = frozenset(("positive", "neutral", "negative"))
_NEGATORS = frozenset((
    "no", "not", "never", "without", "hindi", "di", "wala", "walang",
    "wlang", "hinde", "hnd", "dont", "doesnt", "didnt", "isnt",
))
_MAX_REVIEW = 5000


def _normalize(value: str) -> str:
    """Preserve tokens while treating punctuation as spaces, including Taglish."""
    plain = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[^\W_]+", plain, re.UNICODE))


@lru_cache(maxsize=1)
def _profiles() -> dict[str, dict[str, Any]]:
    payload = json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = payload["profiles"]
    assert set(profiles) == set(CATEGORIES) - {OTHER}, (
        "Category context profile coverage must match exactly 49 known types"
    )
    for slug, profile in profiles.items():
        for side in ("positive_phrases", "negative_phrases"):
            if not isinstance(profile.get(side), list) or not all(
                isinstance(s, str) and _normalize(s) for s in profile[side]
            ):
                raise ValueError(f"Invalid {side} for {slug}")
    return profiles


@lru_cache(maxsize=100)
def _phrases(category: str, polarity: str) -> tuple[str, ...]:
    profile = _profiles()[category]
    return tuple(sorted({_normalize(s) for s in profile[f"{polarity}_phrases"]}, key=len, reverse=True))


def _find_context(text: str, phrases: tuple[str, ...]) -> tuple[bool, bool, str | None]:
    """(unnegated match, negated match, first matched profile phrase).

    No substring hits inside larger words. A preceding denial within four
    words prevents any candidate signal, even for a heavily negated review.
    """
    good, denied, witness = False, False, None
    for phrase in phrases:
        match = re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text)
        if match is None:
            continue
        left = text[:match.start()].split()[-4:]
        if any(word in _NEGATORS for word in left):
            denied = True
            continue
        good = True
        witness = phrase
        break
    return good, denied, witness


def check(
    review: Any,
    listing: Mapping[str, Any] | None,
    initial_label: str | None,
) -> dict[str, Any] | None:
    """Read-only per-review check: identify likely context and compare labels.

    This assessment is metadata only. Even when a profile phrase conflicts
    with XLM-R, it does NOT prove XLM-R was wrong. This function never assigns
    the authoritative predicted sentiment or triggers a hazard.
    """
    if not isinstance(listing, Mapping) or initial_label not in _LABELS:
        return None
    category = classify_listing({"name": str(listing.get("name") or "")})
    base = {
        "revision": REVISION,
        "stage": "after_initial_sentiment_before_conclusion",
        "source": "product_title_plus_review_phrase",
        "product_category": category,
        "initial_label": initial_label,
        "status": "no_signal",
        "context_signal": None,
        "matched_profile_phrase": None,
        "used_for_decision": False,
        "sentiment_overridden": False,
    }
    if category == OTHER:
        return {**base, "status": "unclassified"}
    text = str(review or "")
    if not text.strip() or len(text) > _MAX_REVIEW:
        return {**base, "status": "no_signal"}
    norm = _normalize(text)
    if not norm:
        return {**base, "status": "no_signal"}

    # If both kinds of phrases occur or an explicit denial is found, abstain.
    positive, pos_denied, pos_phrase = _find_context(norm, _phrases(category, "positive"))
    negative, neg_denied, neg_phrase = _find_context(norm, _phrases(category, "negative"))
    if pos_denied or neg_denied or (positive and negative):
        return {**base, "status": "ambiguous"}
    if not positive and not negative:
        return base
    signal = "positive" if positive else "negative"
    # A lexical indication is NOT a verified human annotation.
    return {
        **base,
        "status": "agrees" if signal == initial_label else "differs",
        "context_signal": signal,
        "matched_profile_phrase": pos_phrase if positive else neg_phrase,
    }
