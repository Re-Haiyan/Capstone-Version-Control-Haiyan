"""Conservative source-linked safety QA queue over the *historical* evaluation pack.

This is an AI-assisted / keyword-aided evidence *review queue*, NOT a new
model or a labeler. The detector deliberately recognises only narrow,
firsthand-looking phrasings; a missed match is not evidence that no hazard was
reported. Results never change a live verdict, score human annotations or
claim validated precision/recall.

Usage:
  python research/product_specific_conclusions/ai_annotation/safety_source_audit.py
  python research/product_specific_conclusions/ai_annotation/safety_source_audit.py --out-json /tmp/safety.json --out-csv /tmp/safety.csv

The written reports contain *product IDs, review numbers and issue flags only*:
no raw review text or names, which may contain privacy-sensitive content.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "human_eval_pack"

# Deliberately narrow *event candidates*, not exhaustive safety-language rules.
# A buyer saying "does not overheat" must not turn into a direct event.
DIRECT_PATTERNS: dict[str, re.Pattern[str]] = {
    "fire_or_explosion": re.compile(
        r"\b(?:caught\s+(?:on\s+)?fire|(?:was|is|went|burst|set)\s+on\s+fire|"
        r"explod(?:e|ed|ing|es)|explosion|pumutok|sumabog|nasunog|nagliyab)\b",
        re.I,
    ),
    "burning_smoke": re.compile(
        r"\b(?:smell(?:ed|s)?\s+(?:of\s+)?smoke|smell(?:ed|s)?\s+(?:like\s+)?"
        r"burning|amoy\s+sunog|nangamoy\s+sunog|"
        r"burn(?:ed|t)\s+(?:out|itself)|"
        r"(?:smoke|smoked|smoking)\s+(?:came|coming|from|out))\b",
        re.I,
    ),
    "sparking_or_shock": re.compile(
        r"\b(?:spark(?:s|ed|ing)?|electric\s+shock|electrocut(?:ed|ion)|nakuryente)\b",
        re.I,
    ),
    "overheating": re.compile(
        r"\b(?:overheat(?:s|ed|ing)?|nagooverheat|"
        r"mabilis\s+umin(?:it|et)|sobrang\s+init\s+(?:ng|yung|ang)\s+(?:charger|adap|power))\b",
        re.I,
    ),
    "skin_reaction": re.compile(
        r"\b(?:mahapdi\s+(?:sya\s+)?sa\s+balat|"
        r"nakakatigyawat|nagkapimples|nagka\s+(?:rash|pantal)|"
        r"nangati\s+(?:ako|balat\s+ko)|gave\s+me\s+(?:a\s+)?rash|"
        r"burn(?:ed|t)\s+my\s+skin)\b",
        re.I,
    ),
}

DENIAL_NEAR = re.compile(
    r"\b(?:no|not|never|without|doesn['’]?t|didn['’]?t|won['’]?t|"
    r"walang|hindi|di|wala|d)\b",
    re.I,
)
DENIAL_PHRASES = re.compile(
    r"\b(?:no|without|walang|hindi|di)\s+(?:\w+\s+){0,3}"
    r"(?:smoke|usok|overheat\w*|burn\w*|rash|pantal|spark\w*)\b"
    r"|\b(?:doesn['’]?t|didn['’]?t|not|never)\s+overheat\w*\b",
    re.I,
)
AUTHENTICITY_ALLEGATION = re.compile(
    r"\b(?:counterfeit|fake\s+(?:item|product|charger|brand)|"
    r"peke\s+(?:ang|ung|yung|po\b|item|product)|"
    r"(?:not|isn['’]?t|hindi|di)\s+(?:an?\s+)?original\b|"
    r"not\s+(?:a\s+)?genuine\b)\b",
    re.I,
)

SAFETY_COUNT_PATTERNS = (
    re.compile(r"\b(?P<count>one|\d+)\s+reviews?\s+describes?\s+a\s+possible\s+safety\s+problem\b", re.I),
    re.compile(r"\b(?P<count>one|\d+)\s+reviews?\s+mention(?:s|ing)?\s+a\s+potential\s+safety\s+concern\b", re.I),
)
AUTH_COUNT_PATTERNS = (
    re.compile(r"\b(?P<count>one|\d+)\s+reviews?\s+questions?\s+whether\s+the\s+product\s+is\s+genuine\b", re.I),
    re.compile(r"\bpossible\s+authenticity\s+concerns?\s*\(\s*(?P<count>\d+)\s+reviews?\s*\)", re.I),
)


def _count_claim(text: str, patterns: tuple[re.Pattern[str], ...]) -> int | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            raw = match.group("count").lower()
            return 1 if raw == "one" else int(raw)
    return None


def _denied(text: str, match: re.Match[str]) -> bool:
    # Only a short window within the same clause may negate a cue; a later
    # explicit explosion after "but" must still be flagged.
    prefix = re.split(r"[.!?;]|\b(?:but|however|pero|kaso|although|though)\b",
                      text[:match.start()], flags=re.I)[-1]
    before = " ".join(re.findall(r"[\w’']+", prefix)[-5:])
    return bool(DENIAL_NEAR.search(before))


def review_candidates(text: str) -> tuple[set[str], set[str], bool]:
    """(direct-looking event cues, denied/benign cues, counterfeit allegations).

    These are *candidates* for review, not truth labels. No raw text is emitted.
    """
    direct, denied = set(), set()
    for code, pattern in DIRECT_PATTERNS.items():
        for match in pattern.finditer(text):
            # Feature claims such as "overheating protection" do not describe
            # an incident. Genuine events later in the same review still count.
            suffix = text[match.end():match.end() + 30]
            if code == "overheating" and re.match(
                r"^\s*(?:protection|prevention|control|guard|resistan\w*|proof)\b",
                suffix, re.I
            ):
                denied.add("protection_feature_not_an_event")
            elif _denied(text, match):
                denied.add(code)
            else:
                direct.add(code)
    if DENIAL_PHRASES.search(text):
        denied.add("denial_or_absence")
    return direct, denied, bool(AUTHENTICITY_ALLEGATION.search(text))


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_report(pack: Path = PACK) -> dict:
    reviews_path = pack / "reviews.csv"
    words_path = pack / "words_sheet_A.csv"
    reviews = _load_rows(reviews_path)
    words = _load_rows(words_path)
    if len(reviews) != 5946 or len(words) != 35:
        raise ValueError(f"Unexpected historical pack size: {len(reviews)} reviews / {len(words)} products")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for review in reviews:
        grouped[review["product_id"]].append(review)
    word_ids = [row["product_id"] for row in words]
    if len(set(word_ids)) != 35 or set(word_ids) != set(grouped):
        raise ValueError("Products must match across reviews and system summary pack")

    findings = []
    for summary in sorted(words, key=lambda row: row["product_id"]):
        pid = summary["product_id"]
        evidence: dict[str, list[str]] = defaultdict(list)
        no_event: list[str] = []
        suspected_auth: list[str] = []
        for review in grouped[pid]:
            no = str(review["review_no"])
            direct, denied, possible_fake = review_candidates(review["review_text"])
            for category in direct:
                evidence[category].append(no)
            if denied:
                no_event.append(no)
            if possible_fake:
                suspected_auth.append(no)

        direct_ids = sorted({no for values in evidence.values() for no in values}, key=int)
        denied_ids = sorted(set(no_event), key=int)
        suspected_auth = sorted(set(suspected_auth), key=int)
        summary_texts = [summary[f"text_{i}"] for i in (1, 2)]
        safety_counts = [_count_claim(s, SAFETY_COUNT_PATTERNS) for s in summary_texts]
        auth_counts = [_count_claim(s, AUTH_COUNT_PATTERNS) for s in summary_texts]
        flags = []
        if safety_counts[0] != safety_counts[1]:
            flags.append("summary_safety_count_disagreement")
        if auth_counts[0] != auth_counts[1]:
            flags.append("summary_authenticity_count_disagreement")
        if any(n is not None and n > 0 for n in safety_counts) and not direct_ids:
            flags.append("safety_mentioned_no_direct_event_candidate")
        if direct_ids and all(
            not re.search(r"\b(?:safety|fire|smok\w*|burn\w*|explod\w*|overheat\w*|spark\w*)\b", text, re.I)
            for text in summary_texts
        ):
            flags.append("direct_event_candidate_absent_from_both_summaries")
        if direct_ids and summary["assessment_shown"] == "Too few reviews":
            flags.append("serious_event_candidate_with_too_few_reviews_headline")
        if denied_ids and any(n for n in safety_counts if n is not None):
            flags.append("denials_or_absence_in_source_require_scope_check")

        findings.append({
            "product_id": pid,
            "reviews_in_pack": len(grouped[pid]),
            "system_assessment": summary["assessment_shown"],
            "text1_reported_safety_count": safety_counts[0],
            "text2_reported_safety_count": safety_counts[1],
            "text1_reported_authenticity_count": auth_counts[0],
            "text2_reported_authenticity_count": auth_counts[1],
            "direct_hazard_candidate_review_ids": direct_ids,
            "denied_or_benign_hazard_review_ids": denied_ids,
            "authenticity_allegation_review_ids": suspected_auth,
            "direct_candidate_categories": {key: len(set(value)) for key, value in sorted(evidence.items())},
            "review_flags": flags,
        })

    counts = Counter(code for product in findings for code in product["review_flags"])
    return {
        "audit_type": "heuristic_source_evidence_review_queue",
        "human_evaluation": False,
        "ground_truth": False,
        "verified_error_count": None,
        "allowed_usage": "AI-assisted exploratory source triage only; not accuracy, not live model tuning",
        "sources": {
            "reviews_sha256": hashlib.sha256(reviews_path.read_bytes()).hexdigest(),
            "system_words_sha256": hashlib.sha256(words_path.read_bytes()).hexdigest(),
            "review_rows": len(reviews),
            "product_rows": len(words),
        },
        "flagged_products": sum(bool(row["review_flags"]) for row in findings),
        "flag_counts": dict(sorted(counts.items())),
        "products": findings,
    }


def write_csv(report: dict, output: Path) -> None:
    keys = (
        "product_id", "reviews_in_pack", "system_assessment",
        "text1_reported_safety_count", "text2_reported_safety_count",
        "text1_reported_authenticity_count", "text2_reported_authenticity_count",
        "direct_hazard_candidate_review_ids", "denied_or_benign_hazard_review_ids",
        "authenticity_allegation_review_ids", "direct_candidate_categories", "review_flags",
    )
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in report["products"]:
            values = dict(row)
            for key in ("direct_hazard_candidate_review_ids",
                        "denied_or_benign_hazard_review_ids",
                        "authenticity_allegation_review_ids", "review_flags"):
                values[key] = ";".join(values[key])
            values["direct_candidate_categories"] = json.dumps(values["direct_candidate_categories"], sort_keys=True)
            writer.writerow(values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-csv", type=Path)
    args = parser.parse_args()
    result = build_report()
    if args.out_json:
        args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.out_csv:
        write_csv(result, args.out_csv)
    print("AI-ASSISTED SOURCE QA ONLY; no independent ground truth or model change")
    print("Reviews:", result["sources"]["review_rows"],
          "products:", result["sources"]["product_rows"],
          "products needing contextual review:", result["flagged_products"])
    print("Flags:", result["flag_counts"])


if __name__ == "__main__":
    main()
