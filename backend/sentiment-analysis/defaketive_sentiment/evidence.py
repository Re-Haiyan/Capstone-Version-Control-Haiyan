"""Evidence for each flag a review raises: what, exactly, can be quoted.

A flag can come from three kinds of decision, and only the first can point at words:

* ``keyword_span``: a keyword or rule matched. The matched words are quoted, with their character offsets inside the
  sentence and inside the ORIGINAL review text.
* ``listing_context``: a rule that compares a sentence with the listing (for example a size or an item that differs from
  the title). The sentence is the evidence; no single phrase is.
* ``model_only``: a learned classifier flagged the sentence and nothing in the keyword layer supports it. The sentence is
  quoted, no phrase is highlighted, and the state says so. The flag is **not** suppressed: it stays raised, with an explicit
  "evidence unavailable" state, so a user interface can show it as less certain instead of inventing a quotation.

Nothing here invents text: every quote is a slice of the review as written. A model probability is never reported as an
explanation. The field is additive; it does not change ``review_tags``, ``review_extra_tags`` or any existing key.
"""
from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

KEYWORD_SPAN = "keyword_span"
LISTING_CONTEXT = "listing_context"
MODEL_ONLY = "model_only"
EVIDENCE_STATES = (KEYWORD_SPAN, LISTING_CONTEXT, MODEL_ONLY)


def sentence_offsets(review: object, sentences: Sequence[Mapping[str, Any]]) -> list[int | None]:
    """Where each sentence starts in the original review (None when it cannot be located exactly)."""
    text = str(review or "")
    cursor, starts = 0, []
    for sentence in sentences:
        raw = str(sentence.get("text_raw") or "")
        at = text.find(raw, cursor) if raw else -1
        if at < 0:
            starts.append(None)
            continue
        starts.append(at)
        cursor = at + len(raw)
    return starts


def _valid(span: Any, raw: str) -> bool:
    return (
        isinstance(span, (list, tuple))
        and len(span) == 2
        and 0 <= span[0] < span[1] <= len(raw)
        and raw[span[0] : span[1]].strip() != ""
    )


def evidence_for_review(
    review: object,
    sentences: Sequence[Mapping[str, Any]],
    review_tags: Sequence[str],
    extra_tags: Sequence[str] = (),
) -> dict[str, dict[str, Any]]:
    """{flag: {"state", "sentences", "spans", ...}} for every flag the review raises."""
    starts = sentence_offsets(review, sentences)
    result: dict[str, dict[str, Any]] = {}
    for flag in [*review_tags, *[tag for tag in extra_tags if tag not in review_tags]]:
        spans: list[dict[str, Any]] = []
        carrying: list[int] = []
        listing_parts: dict[str, list[str]] = {}
        learned_score: float | None = None
        for position, sentence in enumerate(sentences):
            tagged = flag in (sentence.get("tags") or ()) or flag in (sentence.get("extra_tags") or ())
            if not tagged:
                continue
            index = int(sentence.get("index", position))
            carrying.append(index)
            raw = str(sentence.get("text_raw") or "")
            for term in [*(sentence.get("terms") or ()), *(sentence.get("extra_terms") or ())]:
                if term.get("category") != flag or term.get("excluded") or term.get("negated") or term.get('evidence_excluded') or term.get('evidence_contextualized'):
                    continue
                span = term.get("span")
                if not _valid(span, raw):
                    continue
                start = starts[position]
                spans.append(
                    {
                        "sentence": index,
                        "start": int(span[0]),
                        "end": int(span[1]),
                        "text": raw[span[0] : span[1]],
                        "review_start": None if start is None else start + int(span[0]),
                        "review_end": None if start is None else start + int(span[1]),
                        "source": "keyword_rule",
                    }
                )
            for context in sentence.get('evidence_context') or []:
                if context.get('category') != flag:
                    continue
                left, right = context['review_start'], context['review_end']
                if str(review or '')[left:right] == context['text']:
                    spans.append({'sentence': index, 'start': None, 'end': None,
                                  'text': context['text'], 'review_start': left,
                                  'review_end': right, 'source': context['source']})
            parts = (sentence.get("extra_context") or {}).get(flag)
            if parts:
                listing_parts[str(index)] = sorted(parts)
            value = (sentence.get("learned") or {}).get(flag)
            if value is not None:
                learned_score = max(learned_score or 0.0, float(value))
        if spans:
            state = KEYWORD_SPAN
        elif listing_parts:
            state = LISTING_CONTEXT
        else:
            state = MODEL_ONLY
        entry: dict[str, Any] = {"state": state, "sentences": carrying, "spans": spans}
        if listing_parts:
            entry["listing_context"] = listing_parts
        if state == MODEL_ONLY:
            entry["note"] = "flagged by a learned classifier; no supporting words found, so none are highlighted"
            if learned_score is not None:
                entry["model_score"] = round(learned_score, 4)
        result[flag] = entry
    return result


# --- optional policy: do not count a flag that has no supporting words --------------------------------------------------
# Measured on the team-supplied labels (research/results/evidence_precision_by_state.json): a defect flag that came only from
# the learned classifier agreed with the label 17% of the time (17 of 101), against 79% for a defect flag with highlighted
# words; quality 17% (3 of 18). OFF by default. When on, those flags are removed from the review and sentence tags and
# listed in ``review_evidence_dropped`` so nothing disappears silently. Safety is never dropped: a missed hazard costs more
# than an unverified one, and counterfeit has no model-only cases.
POLICY_ENV = "DEFAKETIVE_EVIDENCE_POLICY"
POLICY_REQUIRE = "require"
POLICY_SHADOW = "shadow"
DROPPABLE = ("defect", "quality", "not_as_described")


def policy() -> str:
    return os.environ.get(POLICY_ENV, "keep").strip().lower() or "keep"


def droppable(evidence: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The flags the 'require' policy would not count: model-only defect, quality and not-as-advertised (never safety)."""
    return [
        {"flag": flag, "reason": "model_only_no_supporting_words", "sentences": list(entry.get("sentences") or []), "model_score": entry.get("model_score")}
        for flag, entry in evidence.items()
        if entry.get("state") == MODEL_ONLY and flag in DROPPABLE
    ]


def would_drop(evidence: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Shadow mode: what 'require' would drop, reported without dropping anything. Empty unless the policy is 'shadow'."""
    return droppable(evidence) if policy() == POLICY_SHADOW else []


def strip_flags(record: Mapping[str, Any], dropped: list[dict[str, Any]], extra_order: Sequence[str]) -> dict[str, Any]:
    """A copy of an analysis with the dropped flags removed from the sentences it names, as 'require' would have left it."""
    import copy

    clone = copy.deepcopy(dict(record))
    by_sentence: dict[int, set[str]] = {}
    for item in dropped:
        for index in item.get("sentences") or []:
            by_sentence.setdefault(int(index), set()).add(item["flag"])
    for position, sentence in enumerate(clone.get("sentences") or []):
        gone = by_sentence.get(int(sentence.get("index", position)), set())
        if not gone:
            continue
        sentence["tags"] = [tag for tag in sentence.get("tags") or () if tag not in gone]
        if "extra_tags" in sentence:
            sentence["extra_tags"] = [tag for tag in sentence.get("extra_tags") or () if tag not in gone]
        if "high_confidence" in sentence:
            sentence["high_confidence"] = {k: v for k, v in (sentence.get("high_confidence") or {}).items() if k not in gone}
    sentences = clone.get("sentences") or []
    clone["review_tags"] = sorted({tag for s in sentences for tag in s.get("tags") or ()})
    if "review_extra_tags" in clone:
        clone["review_extra_tags"] = [tag for tag in extra_order if any(tag in (s.get("extra_tags") or ()) for s in sentences)]
    clone.pop("review_evidence_would_drop", None)
    return clone


def apply_policy(
    sentences: list[dict[str, Any]],
    review_tags: list[str],
    extra_tags: list[str],
    evidence: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    """Remove model-only defect, quality and not-as-advertised flags when the policy is 'require'. Returns the new tags and the dropped list."""
    if policy() != POLICY_REQUIRE:
        return review_tags, extra_tags, []
    dropped = droppable(evidence)
    if not dropped:
        return review_tags, extra_tags, []
    gone = {item["flag"] for item in dropped}
    for sentence in sentences:
        sentence["tags"] = [tag for tag in sentence.get("tags") or () if tag not in gone]
        if "extra_tags" in sentence:
            sentence["extra_tags"] = [tag for tag in sentence.get("extra_tags") or () if tag not in gone]
        if "high_confidence" in sentence:
            sentence["high_confidence"] = {k: v for k, v in (sentence.get("high_confidence") or {}).items() if k not in gone}
    return [tag for tag in review_tags if tag not in gone], [tag for tag in extra_tags if tag not in gone], dropped
