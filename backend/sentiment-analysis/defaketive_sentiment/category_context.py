"""Cross-category contextual review interpretation, version 2.

Initial sentiment comes from the original XLM-RoBERTa model. This stage checks
whether explicit opinion phrases fit the product, and separately recognizes
*intended behavior* that is not itself praise or a problem. Context is never
an authoritative label and NEVER suppresses any independent hazard checker.

Every category has review phrases and expected/ambiguous traits. A few broad
categories also disambiguate subproducts by title, e.g. heater vs aircon vs fan.
Unrecognized, negated, mixed, or hazard-like language abstains.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Mapping

from .product_category import CATEGORIES, OTHER, classify_listing

REVISION = "category-context-v2"
_PROFILES_PATH = Path(__file__).with_name("category_context_profiles.json")
_LABELS = frozenset(("positive", "neutral", "negative"))
_NEGATORS = frozenset((
    "no", "not", "never", "without", "hindi", "di", "wala", "walang",
    "wlang", "hinde", "hnd", "huwag", "wag", "dont", "doesnt", "didnt", "isnt",
    "don", "doesn", "didn", "isn", "wasn", "weren", "aren", "cant", "cannot",
))
_MAX_REVIEW = 5000
# These are reasons to abstain from treating an otherwise expected feature
# as harmless. They NEVER suppress the independent safety detector.
_SAFETY_WORDS = frozenset((
    "smoke", "smoking", "usok", "umusok", "spark", "sparks", "sparking",
    "shock", "shocks", "nakuryente", "sunog", "nasunog", "burn", "burning",
    "burns", "paso", "napaso", "overheat", "overheats", "overheating",
    "fire", "explosion", "swollen", "namaga", "pumutok", "rash", "rashes",
    "allergy", "allergic", "injury", "injured", "choking", "gas", "leak",
))
# A description of an expected trait must not hide a different complaint
# in the same review. This is deliberately conservative research metadata;
# the independently running hazard model is the ONLY source of safety flags.
_ADVERSE_WORDS = frozenset((
    "sira", "sirang", "nasira", "basag", "basag", "broke", "broken",
    "crack", "cracked", "cracks", "faulty", "defective", "defect", "damage",
    "damaged", "malfunction", "malfunctioning", "failed", "failure",
    "useless", "unusable", "pangit", "palpak", "poor", "terrible", "awful",
    "disappointed", "unsafe", "danger", "dangerous", "burnt", "nasunog",
    "sumabog", "nasisira", "naputol", "putol", "nabitak", "napunit",
    "reklamo", "complaint", "overheated", "leaking", "tagas",
))
_ADVERSE_FAILURE = re.compile(
    r"\b(?:doesn t|didn t|isn t|won t|can t|cannot|not|no|hindi|di|ayaw|"
    r"wala|walang|never)\b.{0,38}\b(?:work|working|function|operate|"
    r"charge|chargeable|heat|heating|cool|cooling|start|turn on|"
    r"gumana|gumagana|uminit|umiinit|lumamig|lumalamig|andar|"
    r"tumatakbo|mag charge|magcharge)\b"
)

_HEAT_EXCESS = re.compile(
    r"\b(?:too|sobrang|masyadong|napaka|excessively|dangerously)\s+"
    r"(?:hot|warm|mainit|init|umiinit|overheating)\b"
)
_HEAT_ON_PART = re.compile(
    r"\b(?:hot|mainit|init|umiinit)\b.{0,35}\b"
    r"(?:plug|socket|wire|wires|cord|cable|casing|housing|handle|battery)\b"
    r"|\b(?:plug|socket|wire|wires|cord|cable|casing|housing|handle|battery)\b"
    r".{0,35}\b(?:hot|mainit|init|umiinit)\b"
)


def _normalize(value: str) -> str:
    """Token boundaries survive Filipino, English and mixed-script reviews."""
    plain = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[^\W_]+", plain, re.UNICODE))


@lru_cache(maxsize=1)
def _profiles() -> dict[str, Any]:
    payload = json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = payload["profiles"]
    if set(profiles) != set(CATEGORIES) - {OTHER}:
        raise ValueError("Category context profiles must cover exactly the named taxonomy")
    for category, profile in profiles.items():
        for polarity in ("positive", "negative", "expected_behavior"):
            field = f"{polarity}_phrases"
            values = profile.get(field)
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and _normalize(value) for value in values
            ):
                raise ValueError(f"{category} has missing or invalid {field}")
        if not isinstance(profile.get("ambiguous_term"), str):
            raise ValueError(f"{category} missing ambiguous term")
    for category, subtypes in payload.get("subtypes", {}).items():
        if category not in profiles or not isinstance(subtypes, list):
            raise ValueError(f"Unknown or invalid subtype category {category}")
        for subtype in subtypes:
            if not isinstance(subtype, dict) or not subtype.get("name"):
                raise ValueError(f"Invalid subtype under {category}")
            for field in ("title_terms", "positive_phrases", "negative_phrases", "expected_behavior_phrases"):
                values = subtype.get(field)
                if not isinstance(values, list) or not all(
                    isinstance(v, str) and _normalize(v) for v in values
                ):
                    raise ValueError(f"Invalid subtype {subtype['name']} {field}")
    return payload


def _present(text: str, phrase: str) -> bool:
    phrase = _normalize(phrase)
    return bool(phrase and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


def _find_context(text: str, phrases: list[str]) -> tuple[bool, bool, str | None]:
    """Exhaust all occurrences, including later negated and unnegated mentions."""
    accepted, denied, matched = False, False, None
    for phrase in dict.fromkeys(_normalize(p) for p in phrases):
        if not phrase:
            continue
        for hit in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text):
            before = text[: hit.start()].split()[-4:]
            if any(w in _NEGATORS for w in before):
                denied = True
            else:
                accepted = True
                matched = matched or phrase
    return accepted, denied, matched


def _subproduct(title: str, category: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    for row in payload.get("subtypes", {}).get(category, ()):
        if any(_present(title, term) for term in row["title_terms"]):
            return row
    return None


def _unsafe_context(text: str) -> bool:
    words = set(text.split())
    return bool(
        words & (_SAFETY_WORDS | _ADVERSE_WORDS)
        or _ADVERSE_FAILURE.search(text)
        or _HEAT_EXCESS.search(text)
        or _HEAT_ON_PART.search(text)
    )


def check(
    review: Any,
    listing: Mapping[str, Any] | None,
    initial_label: str | None,
) -> dict[str, Any] | None:
    """Return audit metadata, never a decision that replaces XLM-R sentiment.

    Expected product behavior (e.g. a heater being hot, a camera being sharp,
    a dumbbell being heavy) does NOT mean Positive; it explicitly abstains.
    Negative and safety complaints still go through the hazard checker.
    """
    if not isinstance(listing, Mapping) or initial_label not in _LABELS:
        return None
    title = str(listing.get("name") or "")
    category = classify_listing({"name": title})
    base = {
        "revision": REVISION,
        "stage": "after_initial_sentiment_before_conclusion",
        "source": "product_title_plus_review_phrase",
        "product_category": category,
        "subproduct": None,
        "initial_label": initial_label,
        "status": "no_signal",
        "context_signal": None,
        "matched_profile_phrase": None,
        "interpretation": None,
        "used_for_decision": False,
        "sentiment_overridden": False,
    }
    if category == OTHER:
        return {**base, "status": "unclassified"}
    review_text = str(review or "")
    if not review_text.strip() or len(review_text) > _MAX_REVIEW:
        return base
    text = _normalize(review_text)
    if not text:
        return base
    try:
        payload = _profiles()
        profile = payload["profiles"][category]
        subtype = _subproduct(_normalize(title), category, payload)
        base["subproduct"] = subtype["name"] if subtype else None
        pos = list(profile["positive_phrases"]) + (list(subtype["positive_phrases"]) if subtype else [])
        neg = list(profile["negative_phrases"]) + (list(subtype["negative_phrases"]) if subtype else [])
        expected = list(profile["expected_behavior_phrases"]) + (list(subtype["expected_behavior_phrases"]) if subtype else [])
        positive, pos_denied, pos_match = _find_context(text, pos)
        negative, neg_denied, neg_match = _find_context(text, neg)
        expected_hit, expected_denied, expected_match = _find_context(text, expected)
        # No generic adjective alone can tell whether the shopper is happy.
        ambiguous_trait = _present(text, profile["ambiguous_term"])
    except (OSError, ValueError, KeyError, TypeError, re.error):
        return {**base, "status": "unavailable"}

    # Never endorse a review describing damage or injury just because it
    # also mentions an expected feature (e.g. a hot heater with a hot plug).
    danger = _unsafe_context(text)
    if pos_denied or neg_denied or (positive and negative) or (expected_denied and not negative):
        # "hindi umiinit ang heater" can match a valid explicit failure as
        # well as a denied expected trait. The failure remains a complaint.
        return {**base, "status": "ambiguous", "interpretation": "mixed_or_negated"}
    if danger and (positive or expected_hit or not negative):
        # A risk cue is never evidence of intended behavior or praise.
        return {**base, "status": "ambiguous", "interpretation": "possible_hazard"}
    if positive or negative:
        signal = "positive" if positive else "negative"
        return {
            **base,
            "status": "agrees" if signal == initial_label else "differs",
            "context_signal": signal,
            "matched_profile_phrase": pos_match if positive else neg_match,
            "interpretation": "explicit_praise" if positive else "explicit_complaint",
        }
    if expected_hit:
        # An ordinary feature is not evidence the reviewer liked the product.
        # Explicit negative reports already took precedence above.
        return {
            **base,
            "status": "expected_behavior",
            "matched_profile_phrase": expected_match,
            "interpretation": "intended_product_behavior",
        }
    if ambiguous_trait:
        return {
            **base, "status": "ambiguous",
            "interpretation": "context_dependent_trait",
            "matched_profile_phrase": _normalize(profile["ambiguous_term"]),
        }
    return base
