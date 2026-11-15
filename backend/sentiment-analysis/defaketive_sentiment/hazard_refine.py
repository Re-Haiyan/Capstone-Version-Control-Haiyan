"""Rules hf1: a last, small refinement of the sentence tags (research/hazard_f1/, November 2026).

Written from the false flags and misses of the deployed checker on a development sample of real reviews (HD1), never from
a test file. It runs after every existing rule and model, and it is OFF unless DEFAKETIVE_HAZARD_REFINE says otherwise:

    DEFAKETIVE_HAZARD_REFINE = 0 (default) | adopted | precision | recall | all

"adopted" is the part that passed the adoption rule on the unseen validation set (research/hazard_f1/results.md): the
not_as_described additions only.

"precision" only REMOVES a flag, each time for a stated reason recorded on the sentence under "suppressed".
"recall" only ADDS a flag, with the matched words as its evidence. Neither can raise a safety ALERT on its own: an added
safety term is never created here, and the severe-safety rules are untouched.
"""
from __future__ import annotations

import os
import re
from typing import Any

REVISION = "hf1"
SAFETY, DEFECT, COUNTERFEIT, QUALITY, NOT_AS_DESCRIBED = "safety", "defect", "counterfeit", "quality", "not_as_described"
EXTRA = (QUALITY, NOT_AS_DESCRIBED)


def mode() -> str:
    value = os.environ.get("DEFAKETIVE_HAZARD_REFINE", "0").strip().lower()
    return value if value in ("adopted", "precision", "recall", "all") else "0"


# --- precision: a flag that the sentence does not support ----------------------------------------------------------------
_REACTION = r"(?:nangati|nangangati|makati|kati|itch\w*|allerg\w*|rash\w*|irritat\w*|break\s?-?outs?|nag\s?-?b[er]+e?\s?-?break\s?-?out|pimples?|hives|namula|mahapdi)"
_DENIED_REACTION = re.compile(
    rf"\b(?:hindi|hinde|hnd|di|d|never|not|no|wala|walang|without|non|zero)\b[\s-]+(?:\w+\s+){{0,2}}{_REACTION}|{_REACTION}[\s-]*free\b", re.I
)
_REACTION_RE = re.compile(rf"\b{_REACTION}", re.I)
_OTHER_PRODUCT = re.compile(r"\b(?:sa|with|from|on|using|gamit\s+ang)\s+(?:ibang|other|another|dating|previous|old)\s+(?:\w+\s+)?(?:products?|brands?|cleansers?|sunscreens?|shampoos?|soaps?|sabon)\b", re.I)
_HARD_HAZARD = re.compile(r"\b(?:sunog|nasunog|usok|umusok|smoke|fire|apoy|shock|kuryente|na-?ground|spoil\w*|expired|panis|bulok|suka|nagsuka|vomit\w*|hospital|sugat|injur\w*|sharp|matalim)\b", re.I)
_BURNT = re.compile(r"\bsunog\b", re.I)
_FOOD = re.compile(r"(?:\b(?:kanin|rice|sinaing|tutong|ulam|pagkain|food|luto|niluto|naluto|fries|chicken|manok|isda|karne)\b|\U0001F35A)", re.I)
_ELECTRIC_BURN = re.compile(r"\b(?:amoy|nangangamoy|nag\s?-?aamoy|usok|umusok|saksak\w*|plug|wire|kuryente|charger|adapter|cord|socket|outlet|plastic)\b", re.I)
_FAKE_NON_PRODUCT = re.compile(r"\b(?:fake|peke|pekeng)\s+(?:na\s+|ang\s+|yung\s+|ung\s+)?(?:video|videos|review|reviews|rating|ratings|promo\w*|advertis\w*|ads?|account|proof|unboxing|tracking|booking|engagement|likes?)\b", re.I)
_FAKE = re.compile(r"\b(?:fake|peke|pekeng|counterfeit|not\s+(?:original|genuine|legit|authentic)|hindi\s+(?:original|orig|legit))\b", re.I)


def _text(item: dict[str, Any]) -> str:
    return str(item.get("text_raw") or item.get("text_normalized") or "")


def _drop(item: dict[str, Any], tag: str, why: str) -> None:
    if tag in EXTRA:
        item["extra_tags"] = [t for t in item.get("extra_tags") or [] if t != tag]
    else:
        item["tags"] = [t for t in item.get("tags") or [] if t != tag]
        (item.get("scores") or {}).pop(tag, None)
        (item.get("high_confidence") or {}).pop(tag, None)
    item.setdefault("suppressed", {})[tag] = f"{REVISION}:{why}"


def _keyword_terms(item: dict[str, Any], category: str) -> list[dict[str, Any]]:
    return [t for t in (item.get("terms") or []) + (item.get("extra_terms") or []) if t.get("category") == category and not t.get("negated") and str(t.get("ngram") or "").strip()]


def _precision(item: dict[str, Any]) -> None:
    text = _text(item)
    tags = set(item.get("tags") or [])
    extra = set(item.get("extra_tags") or [])
    if SAFETY in tags and not _HARD_HAZARD.search(text):
        # "hindi ako nangati", "no irritation": the reaction is denied, not reported.
        if _DENIED_REACTION.search(text) and not _REACTION_RE.search(_DENIED_REACTION.sub(" ", text)):
            _drop(item, SAFETY, "reaction denied")
        # "nagbe-breakout ako sa ibang products": the reaction was to another product.
        elif _REACTION_RE.search(text) and _OTHER_PRODUCT.search(text):
            _drop(item, SAFETY, "reaction to another product")
    if SAFETY in set(item.get("tags") or []) and _BURNT.search(text) and _FOOD.search(text) and not _ELECTRIC_BURN.search(text):
        # "sunog ang kanin": the food was burnt, which is poor cooking, not a fire or a burning smell.
        _drop(item, SAFETY, "burnt food, not a burning product")
    if COUNTERFEIT in tags and _FAKE_NON_PRODUCT.search(text) and not _FAKE.search(_FAKE_NON_PRODUCT.sub(" ", text)):
        # "the seller provided a fake video", "fake reviews": not a claim that the product is counterfeit.
        _drop(item, COUNTERFEIT, "fake video, review or promotion, not the product")
    if DEFECT in tags and _REACTION_RE.search(text) and not _keyword_terms(item, DEFECT):
        # A skin or allergy reaction is a safety report; the learned defect model alone called it a defect.
        _drop(item, DEFECT, "reaction sentence flagged as defect by the model only")
    if NOT_AS_DESCRIBED in extra and _OTHER_PRODUCT.search(text):
        terms = _keyword_terms(item, NOT_AS_DESCRIBED)
        if terms and all(re.fullmatch(r"(?:ibang|other)\s+products?", str(t.get("ngram")).strip(), re.I) for t in terms):
            _drop(item, NOT_AS_DESCRIBED, "'other products' names what was used before, not a wrong item")


# --- recall: reports the lists do not know ----------------------------------------------------------------------------------
_FREEBIE = r"(?:freebies?|free\s?-?bie\w*|free\s+(?:gift|shaker|item|items|pouch|battery|fan|kettle)|mystery\s+gift)"
_ADD = (
    (NOT_AS_DESCRIBED, "buy one take one, one came", re.compile(r"\bbuy\s*(?:1|one|2|two)\s*(?:take|get|gift|free)\s*(?:1|one|2|two)\b[^.!?]{0,80}?\b(?:only|isa\s+lang|iisa|isang|1\s+lang|one\s+only|halos\s+kalahati)\b", re.I)),
    (NOT_AS_DESCRIBED, "promised freebie missing", re.compile(rf"\b(?:no|wala|walang|never|didn.?t|did\s+not|not)\b[^.!?]{{0,30}}\b{_FREEBIE}|\b{_FREEBIE}\b[^.!?]{{0,45}}\b(?:wala|not\s+included|wasn.?t\s+included|never\s+(?:got|get|received)|did\s+not\s+(?:get|receive)|didn.?t\s+(?:get|receive))\b", re.I)),
    (NOT_AS_DESCRIBED, "items missing", re.compile(r"\b(?:daming|maraming|may)\s+kulang\b|\bkulang\s+ang\s+dumating\b", re.I)),
    (NOT_AS_DESCRIBED, "a different item came", re.compile(r"\biba\s+(?:naman\s+)?ang\s+(?:binibigay|binigay|pinadala|dumating)\b|\bhindi\s+(?:naman\s+)?(?:realme|xiaomi|samsung|apple|anker|infinix|vivo|oppo|logitech|original)\s+ang\s+dumating\b", re.I)),
    (QUALITY, "poor material or sound", re.compile(r"\b(?:pangit|panget)\s+(?:pa\s+)?(?:ng\s+|ang\s+|yung\s+|ung\s+)?(?:tela|tila|tunog|sound|sounds|materyal|material)\b|\b(?:hindi|hinde|di)\s+(?:maganda|mgnda|mganda)\s+(?:ang\s+|yung\s+)?(?:tunog|sound|tela)\b", re.I)),
    (QUALITY, "will not last", re.compile(r"\bmukhang\s+(?:hindi|di)\s+tatagal\b|\b(?:hindi|di)\s+(?:din\s+|rin\s+)?(?:masyadong\s+)?matibay\b", re.I)),
    (QUALITY, "weak or broken-up sound, blurred picture", re.compile(r"\bputol\s*-?\s*putol\s+ang\s+(?:sounds?|tunog)\b|\bmahina\s+(?:ang\s+)?(?:vocal|vocals)\b|\b(?:is|are|was|were|mag|nag)\s*-?\s*blur+(?:ed|red|y)?\b", re.I)),
    (DEFECT, "leaks", re.compile(r"\bnag\s?-?le+\s?-?leak\b|\bnag\s?-?li\s?-?leak\b|\bcausing\s+leaks?\b", re.I)),
    (DEFECT, "arrived deformed or unsealed", re.compile(r"\b(?:items?|product|unit)\s+(?:was|is|were|are)\s+deform\w*|\b(?:no|walang)\s+(?:plastic\s+)?seal\b|\bpump\s+is\s+already\s+open\b", re.I)),
    (DEFECT, "a function does not work", re.compile(r"\bunable\s+to\s+(?:turn|use|charge|connect|open|start|control)\b", re.I)),
    (COUNTERFEIT, "not like the original", re.compile(r"\b(?:doesn.?t|does\s+not|hindi)\s+(?:taste|look|smell)\b[^.!?]{0,25}\blike\s+the\s+original\b", re.I)),
)


def _recall(item: dict[str, Any], only: tuple[str, ...] | None = None) -> None:
    text = _text(item)
    if not text:
        return
    for label, why, pattern in _ADD:
        if only is not None and label not in only:
            continue
        present = set(item.get("tags") or []) | set(item.get("extra_tags") or [])
        if label in present or label in (item.get("suppressed") or {}):
            continue
        match = pattern.search(text)
        if not match:
            continue
        term = {"ngram": match.group(0).lower(), "category": label, "severity": 2, "negated": False, "span": [match.start(), match.end()], "rule": f"{REVISION}:{why}"}
        if label in EXTRA:
            item["extra_tags"] = list(item.get("extra_tags") or []) + [label]
            item.setdefault("extra_terms", []).append(term)
        else:
            item["tags"] = sorted(set(item.get("tags") or []) | {label}, key=(SAFETY, DEFECT, COUNTERFEIT).index)
            item.setdefault("terms", []).append(term)
            item.setdefault("scores", {})[label] = 2.0
            item.setdefault("high_confidence", {})[label] = True


def refine_sentences(sentences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply rules hf1 in place to the tagged sentences of one review, according to DEFAKETIVE_HAZARD_REFINE."""
    how = mode()
    if how == "0":
        return sentences
    for item in sentences:
        if how in ("precision", "all"):
            _precision(item)
        if how in ("recall", "all"):
            _recall(item)
        if how == "adopted":
            _recall(item, only=(NOT_AS_DESCRIBED,))
        if how != "0":
            item["refine_revision"] = REVISION
    return sentences
