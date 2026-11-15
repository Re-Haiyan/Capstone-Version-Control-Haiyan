"""Full-corpus, source-locked AI annotation quality audit (DEVELOPMENT ONLY).

Processes ALL 3,400 Claude-labelled dev/candidate rows. Generates:
* 3,400-row immutable-label quality registry (no review text)
* 3,400-row blind full-text reannotation sheet
* <=480-row prioritized blind full-text review packet
* matching coordinator-only risk/AI-label crosswalk
* aggregate audit JSON with exact source counts

No automatic sentiment changes, model predictions, stars, or scoring of frozen
final tests or Phase-3 confirmation. Every suggested correction requires
separate versioned, attributable adjudication.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
HERE = Path(__file__).resolve().parent
LABELS = frozenset(("positive", "negative", "neutral", "mixed", "unclear"))
TAGS = frozenset(("mixed", "delivery-only", "no-opinion"))
CONFIDENCE = frozenset(("high", "low"))
SPLITS = (
    ("dev", "dev_pool_sheet.csv", "dev_pool_sheet_ai_v1.csv", 400),
    ("candidates", "neutral_candidate_pool.csv", "neutral_candidate_pool_ai_v1.csv", 3000),
)
# These patterns create FLAGS, never source-of-truth labels. They are not validated
# regex classifiers and should not be used for automatic sentiment correction.
DEFECT = re.compile(
    r"(?i)(?:\b(?:di|hindi|hnd|walang)\s+(?:gumagana|umandar|working|nagc?cha[r]?ge|nagana|nagfu?function)"
    r"|\b(?:not\s+working|doesn.t\s+work|stopped\s+working|broke[n]?|defective|fake|counterfeit)"
    r"|\b(?:(?:arrived|received|came|item|unit|product)\s+damaged|damaged\s+(?:item|unit|product|on\s+arrival))\b"
    r"|\b(?:sira|nasira|sirang|mabagal|wrong\s+(?:item|size|product))\b"
    r"|(?:madaling|mabilis|bilis|agad)\s+malowbat\b)"
)
PERSONAL = re.compile(r"(?i)\b(?:ako|ko|akin|namin|nagamit|nasubukan|nakita|bought|"
                      r"i|my|mine|we|our|tried|tested|received|works|working|"
                      r"nagustuhan|ginamit)\b")
EVALUATIVE = re.compile(
    r"(?i)\b(?:maganda|ganda|napakaganda|sulit|maayos|love|excellent|great|"
    r"best|worth|nice|good|disappointed|bad|poor|terrible|impressive|"
    r"quality|defect|broken|legit|horrible)\b"
)
NO_USE = re.compile(r"(?i)\b(?:di|hindi|not|never|haven.t)\s+(?:ko\s+pa\s+)?(?:natry|nasubukan|tested|tried|used)\b")
SEGMENTS = re.compile(r"[^.!?,;]+")
SALT = "defaketive-phase6-annotation-audit-v1"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = ("blob " + str(len(data)) + "\0").encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def verify_protected(root_repo: Path = REPO, manifest: Path = HERE/"protected_git_blobs.json"):
    config = json.loads(manifest.read_text(encoding="utf-8"))
    for relative, expected in config["protected_blob_shas"].items():
        path = root_repo / relative
        if not path.is_file():
            raise ValueError("Protected source missing: " + relative)
        got = git_blob_sha(path)
        if got != expected:
            raise ValueError("Protected source modified: " + relative + "; expected " + expected + ", got " + got)
    return len(config["protected_blob_shas"])


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        header = reader.fieldnames or []
        if len(header) != len(set(header)):
            raise ValueError("Duplicate header in " + path.name)
        rows = list(reader)
    if not rows or any(not r.get("id", "").strip() for r in rows):
        raise ValueError("Missing id in " + path.name)
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate row ID in " + path.name)
    if any(None in r or r.get(None) is not None for r in rows):
        raise ValueError("Malformed CSV columns in " + path.name)
    return {r["id"]: r for r in rows}


def grouped_title(title: str) -> str:
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", title).lower()))


def validate_pair(original, completed, split, expected):
    if len(original) != expected or len(completed) != expected or set(original) != set(completed):
        raise ValueError(f"{split}: missing/extra rows (expected {expected})")
    for rid, row in completed.items():
        src = original[rid]
        for field in ("id", "review_text", "product", "category_group", "platform", "language_hint"):
            if src.get(field, "") != row.get(field, ""):
                raise ValueError(f"{split}:{rid}: original {field} changed")
        label = row["sentiment"].strip().lower()
        conf = row["confidence"].strip().lower()
        tags = [t.strip().lower() for t in row["tags"].split(";") if t.strip()]
        if label not in LABELS or conf not in CONFIDENCE:
            raise ValueError(f"{split}:{rid}: invalid label/confidence")
        if len(tags) != len(set(tags)) or not set(tags) <= TAGS:
            raise ValueError(f"{split}:{rid}: invalid/duplicate tags")
        if ("mixed" in tags) != (label == "mixed" or (
             label in {"positive","negative"} and "mixed" in tags)):
            if label == "mixed" and "mixed" not in tags:
                raise ValueError(f"{split}:{rid}: mixed label requires mixed tag")
        if "mixed" in tags:
            if label in {"neutral", "unclear"}:
                raise ValueError(f"{split}:{rid}: mixed tag incompatible with {label}")
            if not row["positive_aspect"].strip() or not row["negative_aspect"].strip():
                raise ValueError(f"{split}:{rid}: missing mixed aspects")
        if "no-opinion" in tags and label not in {"neutral", "unclear"}:
            raise ValueError(f"{split}:{rid}: no-opinion tag incompatible with {label}")
        if not row.get("rationale", "").strip():
            raise ValueError(f"{split}:{rid}: missing rationale")
    return len(completed)


def flags_for(row, second_label: str | None, risk_info: dict) -> list[str]:
    label = row["sentiment"].strip().lower()
    confidence = row["confidence"].strip().lower()
    tags = {t.strip().lower() for t in row["tags"].split(";") if t.strip()}
    text = row["review_text"]
    findings: list[str] = []
    if second_label and second_label != label:
        findings.append("ai_disagreement")
    if confidence == "low":
        findings.append("low_confidence")
    if label == "neutral" and "no-opinion" in tags:
        if len(text) > 170:
            findings.append("neutral_long_review_first_pass_truncation_risk")
        if len(text) > 170 and PERSONAL.search(text[170:]) and EVALUATIVE.search(text[170:]):
            findings.append("personal_evaluation_after_170")
        if DEFECT.search(text):
            findings.append("negative_cue_in_no_opinion")
        if PERSONAL.search(text) and EVALUATIVE.search(text):
            findings.append("personal_evaluation_in_no_opinion")
    if "delivery-only" in tags and DEFECT.search(text):
        findings.append("delivery_only_and_defect_cue")
    if label == "positive" and DEFECT.search(text):
        findings.append("positive_with_defect_cue")
    if label == "negative" and NO_USE.search(text) and not DEFECT.search(text):
        findings.append("negative_with_no_use_cue")
    if risk_info.get("list_shape"):
        findings.append("template_like_review")
        if label == "neutral" and EVALUATIVE.search(text):
            findings.append("s4_evaluative_template_neutral")
    if label == "neutral" and row["language_hint"].strip().lower() in ("filipino", "taglish"):
        findings.append("filipino_taglish_neutral_underrepresented")
    if 165 <= len(text) <= 175 and text[-1:] not in (".","!","?","。"):
        findings.append("source_text_maybe_cut_at_170")
    if len(text.split()) <= 3 and label != "unclear":
        findings.append("extremely_short_review")
    return sorted(set(findings))


def shape(text: str) -> dict:
    parts = [part.strip() for part in SEGMENTS.findall(text) if part.strip()]
    looks_like_list = (len(parts) >= 3
                       and all(len(part.split()) <= 12 for part in parts)
                       and not PERSONAL.search(text))
    return {"list_shape": looks_like_list, "length": len(text)}


def score(flags):
    weights = {
        "ai_disagreement": 100,
        "negative_cue_in_no_opinion": 95,
        "personal_evaluation_after_170": 90,
        "delivery_only_and_defect_cue": 75,
        "positive_with_defect_cue": 65,
        "personal_evaluation_in_no_opinion": 65,
        "filipino_taglish_neutral_underrepresented": 60,
        "source_text_maybe_cut_at_170": 45,
        "neutral_long_review_first_pass_truncation_risk": 35,
        "negative_with_no_use_cue": 35,
        "low_confidence": 25,
        "s4_evaluative_template_neutral": 20,
        "template_like_review": 10,
        "extremely_short_review": 10,
    }
    return max((weights.get(flag, 0) for flag in flags), default=0)


def priority(point):
    return ("critical" if point >= 90 else
            "high" if point >= 60 else
            "medium" if point >= 25 else
            "low")


def annotate(root: Path = ROOT):
    second = read_csv(root/"phase5"/"gpt6_second_ai_labels_v1.csv")
    output = []
    checked = []
    for split, orig_name, labelled_name, expected in SPLITS:
        raw = read_csv(root / "annotation" / orig_name)
        old = read_csv(root / "annotation" / "ai_labelled" / labelled_name)
        checked.append((split, validate_pair(raw, old, split, expected)))
        for rid, row in old.items():
            gpt = second.get(rid)
            risk = shape(row["review_text"])
            flags = flags_for(row, gpt["sentiment"].strip().lower() if gpt else None, risk)
            point = score(flags)
            output.append({
                "id": rid, "split": split,
                "label": row["sentiment"].strip().lower(),
                "confidence": row["confidence"].strip().lower(),
                "tags": row["tags"],
                "language": row["language_hint"].strip().lower(),
                "product_group_title": grouped_title(row["product"]),
                "title": row["product"],
                "review_text": row["review_text"],
                "platform": row["platform"],
                "gpt6_label": gpt["sentiment"].strip().lower() if gpt else "",
                "flags": flags, "score": point,
                "priority": priority(point),
                "risk_info": risk,
                "verification_status": "unverified_ai_label",
            })
    if len(output) != 3400 or len({r["id"] for r in output}) != len(output):
        raise ValueError("Development coverage not 3,400 unique rows")
    if len(second) != 140:
        raise ValueError("Second-AI set unexpectedly modified")
    if sum(bool(r["gpt6_label"]) and r["gpt6_label"] != r["label"] for r in output) != 71:
        raise ValueError("Cross-AI disagreement baseline unexpectedly changed")
    return output, checked


def stable_tie(row):
    return hashlib.sha256((SALT + "/" + row["id"]).encode()).hexdigest()


def select_priority_review(rows, maximum=480, cap_per_title=6):
    if maximum < 140:
        raise ValueError("Must allow at least 140 second-AI-reviewed IDs for adjudication")
    # Reserve explicit first priority for all 71 disagreements.
    ordered = sorted(rows, key=lambda r: (-r["score"], stable_tie(r), r["id"]))
    selected = []
    ids = set()
    product_use = collections.Counter()
    def add(row, enforce_cap):
        if row["id"] in ids or len(selected) >= maximum:
            return False
        if enforce_cap and product_use[row["product_group_title"]] >= cap_per_title:
            return False
        ids.add(row["id"])
        selected.append(row)
        product_use[row["product_group_title"]] += 1
        return True
    # Never quietly discard a known cross-provider disagreement.
    for row in ordered:
        if "ai_disagreement" in row["flags"]:
            add(row, False)
    # Guarantee some ordinary controls for a less biased quality estimate.
    control_goal = max(40, maximum//8)
    controls = [r for r in rows if not r["flags"] and r["label"] in ("positive","negative","neutral")]
    for row in sorted(controls, key=stable_tie)[:control_goal*4]:
        if sum(not r["flags"] for r in selected) >= control_goal:
            break
        add(row, True)
    # Include diverse flagged items before filling remaining slots.
    for row in ordered:
        add(row, True)
    # Do not silently drop a small category because of the title cap;
    # any remaining slots are filled with highest-priority reviews.
    for row in ordered:
        add(row, False)
    return selected


def select_random_quality_sample(rows, maximum=200):
    """Pre-declared simple random sample for ANNOTATION quality, not model test.

    This is representative only of the 3,400-row selected development pool,
    which itself is not representative of marketplace natural prevalence.
    """
    rng = random.Random(20261115)
    ordered = sorted(rows, key=lambda r: r["id"])
    return rng.sample(ordered, min(maximum, len(ordered)))


def write_csv(path: Path, fieldnames, rows):
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer = csv.DictWriter(handle,fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def blind_row(row):
    # No previous Claude/GPT-6 labels, tags, scores, flags, ratings or predictions.
    return {
        "id": row["id"], "split": row["split"], "product": row["title"],
        "platform": row["platform"], "language_hint": row["language"],
        "review_text": row["review_text"],
        "sentiment": "", "tags": "", "positive_aspect": "",
        "negative_aspect": "", "confidence": "", "rationale": "",
        "reviewer_id": "", "reviewer_type": "", "policy_version": "",
    }


def emit(rows, out_dir: Path, protected: int, maximum=480, export_blind_text=False):
    out_dir.mkdir(parents=True,exist_ok=True)
    selected = select_priority_review(rows, maximum=maximum)
    random_sample = select_random_quality_sample(rows, maximum=200)
    chosen = {r["id"] for r in selected}
    by_flag = collections.Counter(flag for r in rows for flag in r["flags"])
    by_label = collections.Counter(r["label"] for r in rows)
    by_lang_label = collections.Counter((r["language"],r["label"]) for r in rows)
    by_priority = collections.Counter(r["priority"] for r in rows)
    included = collections.Counter(flag for r in selected for flag in r["flags"])
    quality = {
        "schema": "phase6_dev_annotation_quality_audit_v1",
        "checked_protected_git_blobs": protected,
        "development_rows_checked": len(rows),
        "no_original_labels_modified": True,
        "frozen_test_and_used_confirmation": "integrity-only Git blob check; never scored, relabelled or exported",
        "annotators": "Original Claude Sonnet 5.5, second GPT-6 on 140 difficult cases; AI-assisted not human gold",
        "count_by_original_label": dict(sorted(by_label.items())),
        "counts_by_priority": dict(sorted(by_priority.items())),
        "counts_by_flag": dict(sorted(by_flag.items())),
        "counts_by_language_and_label": {"/".join(k):v for k,v in sorted(by_lang_label.items())},
        "priority_blind_review_packet_rows": len(selected),
        "random_quality_audit_sample_rows": len(random_sample),
        "random_priority_overlap": len({r["id"] for r in random_sample} & chosen),
        "random_sample_scope": "Selected 3400-row AI-labelled development pool, NOT natural marketplace population",
        "priority_blind_packet_flag_coverage": dict(sorted(included.items())),
        "full_blind_review_packet_rows": len(rows) if export_blind_text else 0,
        "full_blind_text_exported": export_blind_text,
        "eligible_for_local_blind_export": len(rows),
        "known_cross_ai_disagreements_in_priority_packet": sum("ai_disagreement" in r["flags"] for r in selected),
        "sample_is_not_random": True,
        "limitations": [
            "Heuristics identify risk but never certify a label as wrong.",
            "All existing labels remain unverified AI-assisted silver labels, not human reference truth.",
            "Priority queue is intentionally enriched; cannot infer population error rate from its agreement.",
            "Template origin and personal-use provenance cannot be verified from text alone.",
            "The original Phase 4 product-ID mapping is missing; no classifier evaluation is performed here.",
            "Original frozen test and already-scored confirmation remain off-limits for label repair/model tuning.",
        ],
    }
    registry_fields=["id","split","original_label","confidence","tags","language","priority",
                     "risk_score","flags","second_ai_disagreed","selected_for_review",
                     "verification_status"]
    write_csv(out_dir/"all_3400_quality_registry.csv",registry_fields,[
        {
            "id":r["id"],"split":r["split"],"original_label":r["label"],
            "confidence":r["confidence"],"tags":r["tags"],"language":r["language"],
            "priority":r["priority"],"risk_score":r["score"],
            "flags":";".join(r["flags"]),
            "second_ai_disagreed":int(bool(r["gpt6_label"]) and r["gpt6_label"]!=r["label"]),
            "selected_for_review":int(r["id"] in chosen),
            "verification_status":r["verification_status"],
        } for r in sorted(rows,key=lambda r:r["id"])
    ])
    write_csv(out_dir/"priority_ids.csv",["id","split"],[
        {"id":r["id"],"split":r["split"]} for r in selected])
    write_csv(out_dir/"random_quality_sample_ids.csv",["id","split"],[
        {"id":r["id"],"split":r["split"]} for r in random_sample])
    if export_blind_text:
        blind_fields=list(blind_row(rows[0]))
        write_csv(out_dir/"all_3400_blind_review.csv",blind_fields,[
            blind_row(r) for r in sorted(rows,key=lambda r:r["id"])])
        write_csv(out_dir/"priority_blind_review.csv",blind_fields,[
            blind_row(r) for r in selected])
        write_csv(out_dir/"random_blind_review.csv",blind_fields,[
            blind_row(r) for r in random_sample])
    coordinator_fields=["id","split","original_Claude_label","second_GPT6_label","language",
                        "priority","flags","current_status","human_adjudicated_label",
                        "adjudicator_id","adjudication_policy","adjudication_date"]
    write_csv(out_dir/"priority_coordinator_only.csv",coordinator_fields,[{
        "id":r["id"],"split":r["split"],"original_Claude_label":r["label"],
        "second_GPT6_label":r["gpt6_label"],"language":r["language"],
        "priority":r["priority"],"flags":";".join(r["flags"]),
        "current_status":"not_human_reviewed","human_adjudicated_label":"",
        "adjudicator_id":"","adjudication_policy":"","adjudication_date":"",
    } for r in selected])
    (out_dir/"annotation_quality_report.json").write_text(
        json.dumps(quality,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8"
    )
    return quality


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("/tmp/defaketive-annotation-quality"))
    parser.add_argument("--maximum-review-rows",type=int,default=480)
    parser.add_argument("--export-blind-text",action="store_true",
                        help="LOCAL ONLY: export full review text for independent reannotation; never upload publicly")
    args=parser.parse_args()
    protected=verify_protected()
    rows,_=annotate()
    result=emit(rows,args.output,protected,args.maximum_review_rows,args.export_blind_text)
    print(json.dumps(result,indent=2,sort_keys=True))
    print("No original label, frozen data or deployed model changed.")


if __name__=="__main__":
    main()
