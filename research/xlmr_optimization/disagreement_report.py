"""Disagreement cases and the (blank) adjudication sheet for A03, from two returned sheets, matched by review ID. Stars and model predictions are never read.

    python research/xlmr_optimization/disagreement_report.py <sheet A done> <sheet B done>
A disagreement is a difference in `sentiment` or in the set of `tags`. The report groups them and attaches the matching policy rule; it never says which annotator is right.
The adjudication sheet has EMPTY final fields; nothing is pre-filled. Both returned sets are AI-assisted (ai_assisted_annotation_methodology.md), so every row carries that status.
"""
import collections, csv, pathlib, re, sys
X = pathlib.Path(__file__).resolve().parent
OUT = X / "final_human_evaluation"
A = {r["id"]: r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8-sig"))}
B = {r["id"]: r for r in csv.DictReader(open(sys.argv[2], encoding="utf-8-sig"))}
PAT = {"okay lang / pwede na": r"\b(?:ok(?:ay)?\s*(?:lang|naman|na)|pwede na|keri lang|so[- ]?so|sakto lang|sapat na)\b", "sulit / value": r"\b(?:sulit|worth|value for money|bang for)\b",
       "not yet tested / not yet used": r"\b(?:not yet|yet to|haven'?t (?:tried|used|tested)|di ko pa|hindi ko pa|will update|update (?:ko|later)|wala pa)\b",
       "delivery / seller": r"\b(?:deliver\w*|rider|ship\w*|courier|packag\w*|packing|seller|parcel|dumating|nadeliver)\b", "feature list / description": r"^(?:[^.!?]{3,70},\s*){3,}",
       "contrast (pero / but / kaso)": r"\b(?:pero|but|kaso|however|although|though|kaya lang)\b", "negation (hindi / di / not / wala)": r"\b(?:hindi|di|not|no|never|wala|walang|ayaw|cannot|can'?t|doesn'?t|didn'?t)\b",
       "sarcasm cue": r"(?:/s\b|yeah right|sure\.\.|ang galing naman|wow ha)", "generic praise": r"\b(?:good|great|nice|ganda|maganda|best|recommended|love|thank)\b"}
def kind(a, b, ta, tb):
    sa, sb = a["sentiment"].strip().lower(), b["sentiment"].strip().lower()
    pair = frozenset((sa, sb))
    if sa != sb:
        if "unclear" in pair: return "unclear vs classified", "policy 3: unclear = a person cannot decide from the text"
        if "mixed" in pair: return "mixed vs single-polarity", "policy S1: mixed = no polarity dominates; otherwise the dominant polarity plus the tag mixed"
        if pair == {"positive", "neutral"}: return "positive vs neutral", "policy S3/S4: lukewarm and feature lists are neutral; explicit praise changes the label"
        if pair == {"positive", "negative"}: return "positive vs negative", "policy 3: the dominant side decides; check for a second clause"
        return "negative vs neutral", "policy 3: neutral = no clear evaluation; a complaint is negative"
    return "same label, different tags", "policy 1/S1/S2/S4: tags mixed, delivery-only, no-opinion"
rows, counts, pats = [], collections.Counter(), collections.Counter()
for i in sorted(set(A) & set(B)):
    a, b = A[i], B[i]
    ta = {t.strip().lower() for t in a["tags"].split(";") if t.strip()}; tb = {t.strip().lower() for t in b["tags"].split(";") if t.strip()}
    if a["sentiment"].strip().lower() == b["sentiment"].strip().lower() and ta == tb:
        continue
    k, rule = kind(a, b, ta, tb)
    found = [n for n, rx in PAT.items() if re.search(rx, a["review_text"], re.I)]
    counts[k] += 1
    for f in found: pats[f] += 1
    rows.append({"provenance_status": "AI-assisted set (not independent human)", "id": i, "disagreement_type": k, "policy_rule": rule, "recurring_pattern": "; ".join(found), "product": a["product"], "review_text": a["review_text"],
                 "label_A": a["sentiment"], "tags_A": a["tags"], "positive_aspect_A": a["positive_aspect"], "negative_aspect_A": a["negative_aspect"], "confidence_A": a["confidence"], "rationale_A": a["rationale"],
                 "label_B": b["sentiment"], "tags_B": b["tags"], "positive_aspect_B": b["positive_aspect"], "negative_aspect_B": b["negative_aspect"], "confidence_B": b["confidence"], "rationale_B": b["rationale"],
                 "any_low_confidence": "yes" if "low" in (a["confidence"], b["confidence"]) else "no"})
with open(OUT / "disagreement_cases.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
ac = ["status", "id", "product", "review_text", "label_A", "tags_A", "positive_aspect_A", "negative_aspect_A", "confidence_A", "rationale_A", "label_B", "tags_B", "positive_aspect_B", "negative_aspect_B", "confidence_B", "rationale_B",
      "final_label", "final_tags", "final_positive_aspect", "final_negative_aspect", "reason_for_final_decision", "policy_version", "adjudicator_id", "date"]
with open(OUT / "adjudication_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=ac); w.writeheader()
    for r in rows:
        w.writerow({"status": "READY for human review: both sets are AI-assisted (ChatGPT); decide each row from the review text and policy v1; keep originals; write only in the final_* columns", **{k: r[k] for k in ac if k in r and k != "status"}, "policy_version": "", "final_label": "", "final_tags": "", "final_positive_aspect": "", "final_negative_aspect": "", "reason_for_final_decision": "", "adjudicator_id": "", "date": ""})
print(len(rows), "disagreements;", dict(counts)); print("patterns among them:", dict(pats.most_common()))
