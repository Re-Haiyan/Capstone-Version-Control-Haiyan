"""Audit of what the evidence policy 'require' would suppress.

    backend\\.venv\\Scripts\\python.exe research\\evidence_policy_audit.py [workers]

Runs the release code (all experimental switches cleared) on the labelled reviews and lists every model-only defect, quality and
not-as-advertised flag the policy would not count: id, split (train = development, test = historical benchmark), product group,
the team-supplied label for that flag (provenance unverified), the model score, the sentence quoted, and an AUTOMATIC triage of why
there is no evidence (a word list, not a judgement). The true flags that would be lost are then read by hand in the audit document.
Writes research/evidence_policy_audit.csv and research/results/evidence_policy_audit.json.
"""
import csv, json, multiprocessing as mp, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for key in [k for k in os.environ if k.startswith("DEFAKETIVE_")]:
    del os.environ[key]
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis")); sys.path.insert(0, str(pathlib.Path(__file__).parent))
_model = None
FLAGS5 = ("defect", "counterfeit", "safety", "not_as_described", "quality")
DENIAL = re.compile(r"(?:wala|walang|no|not|without|hindi|di)\s+(?:\w+\s+){0,3}(?:damage\w*|leak\w*|sira|defect\w*|basag|scratch\w*|dent\w*)|(?:gumagana|works?|working|maayos|okay|ok)\s+(?:pa\s+)?(?:din|naman|ng maayos|xa|pa rin|well|fine)", re.I)
MISSED_CUE = re.compile(r"(?:hindi|di|ayaw|not|doesn.?t|didn.?t|won.?t|can.?t|cannot|no)\s+(?:\w+\s+){0,3}(?:gumana|gumagana|umandar|working|work|function\w*|connect\w*|ma-?read|mag-?charge|charg\w*|nag-?on|on)|ayaw|error|disconnect\w*|nawawala|namatay|nag-?hang|basag|sira\b|broken|crack\w*|leak\w*|tagas|bloat\w*|punit|butas|yupi|dent\w*|scratch\w*|faulty|defective|depekto", re.I)
OTHER_TOPIC = re.compile(r"allerg\w*|rash\w*|makati|itch\w*|nagtae|diarrh\w*|vomit|nagsuka|sumakit|expired|panis|amag\b|usok|sunog|kulang|missing|iba ang|wrong|mali ang|epekto|bumula|bumubula|pumuti|peke|fake|scam|original|nipis|manipis|cheap|mumurahin|late|tagal|delivery|rider|seller|baka\b", re.I)


def triage(text: str) -> str:
    if DENIAL.search(text) and not MISSED_CUE.search(re.sub(DENIAL, " ", text)):
        return "denial_or_praise"
    if MISSED_CUE.search(text):
        return "possible_missed_evidence"
    if OTHER_TOPIC.search(text):
        return "complaint_about_something_else"
    return "no_specific_problem_stated"


def work(items):
    global _model
    if _model is None:
        from defaketive_sentiment import registry
        _model = registry.load_model()
    out = []
    for r in items:
        a = _model.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]})[0]
        from defaketive_sentiment.evidence import droppable
        for d in droppable(a["review_evidence"]):
            quote = " | ".join(s["text_raw"] for s in a["sentences"] if int(s.get("index", -1)) in d["sentences"])
            out.append({"id": r["id"], "split": r["split"], "flag": d["flag"], "model_score": d["model_score"], "quote": quote[:260], "review": r["review_text"][:300],
                        "flags_raised": sorted(set(a["review_tags"]) | set(a.get("review_extra_tags") or []))})
    return out


if __name__ == "__main__":
    from common import load
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    rows, meta = [], {}
    for name, split in (("train_v3", "train"), ("test_v3", "test")):
        for r in load(name):
            meta[r["id"]] = r
    for name, split in (("train_v3", "train"), ("test_v3", "test")):
        rows += [dict(r, split=split) for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high" and r["flags"].strip()]
    found = []
    with mp.Pool(n) as pool:
        for part in pool.imap_unordered(work, [rows[i::n * 4] for i in range(n * 4)]):
            found += part
    out_rows = []
    for d in found:
        m = meta[d["id"]]; k = FLAGS5.index(d["flag"])
        out_rows.append({"id": d["id"], "split": d["split"], "group": m["group"], "flag": d["flag"], "team_label_for_this_flag": int(m["y"][k]), "model_score": d["model_score"],
                         "automatic_triage": triage(d["review"]) if d["flag"] == "defect" else "", "other_flags_raised": ";".join(f for f in d["flags_raised"] if f != d["flag"]), "quote": d["quote"].replace("\n", " "), "review": d["review"].replace("\n", " ")})
    out_rows.sort(key=lambda r: (r["flag"], r["split"], -r["team_label_for_this_flag"], r["id"]))
    with open(ROOT / "research" / "evidence_policy_audit.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys())); w.writeheader(); w.writerows(out_rows)
    summary = {}
    for flag in ("defect", "quality", "not_as_described"):
        for split in ("train", "test"):
            sel = [r for r in out_rows if r["flag"] == flag and r["split"] == split]
            tri = {}
            for r in sel:
                tri.setdefault(r["automatic_triage"] or "-", [0, 0]); tri[r["automatic_triage"] or "-"][0] += 1; tri[r["automatic_triage"] or "-"][1] += r["team_label_for_this_flag"]
            summary[f"{flag}|{split}"] = {"would_drop": len(sel), "of_which_team_labelled_true": sum(r["team_label_for_this_flag"] for r in sel), "triage_(count, labelled_true)": tri}
    json.dump(summary, open(ROOT / "research" / "results" / "evidence_policy_audit.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))
