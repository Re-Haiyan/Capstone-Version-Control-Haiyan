"""Evidence audit: for every flag the deployed checker raises, is there a real, valid highlighted span to quote?

    backend\\.venv\\Scripts\\python.exe research\\evidence_check.py [workers]

Reads the labelled training and test files, runs the deployed checker with the product title, and reports per flag:
flags raised, flags with at least one valid supporting span, flags with no span (model-only), and span validity
problems (out of range, empty, whitespace only). Writes research/results/evidence_check.json.
"""
import collections, csv, json, multiprocessing as mp, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality")
_model = None


def work(rows):
    global _model
    if _model is None:
        from defaketive_sentiment import registry
        _model = registry.load_model()
    out = []
    for r in rows:
        a = _model.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]})[0]
        tags = set(a.get("review_tags") or []) | set(a.get("review_extra_tags") or [])
        stat = {"id": r["id"], "raised": sorted(tags & set(FLAGS)), "with_span": [], "bad_span": 0, "spans": 0, "negated_only": []}
        for flag in stat["raised"]:
            valid = negated = False
            for s in a["sentences"]:
                text = s["text_raw"]
                for t in list(s.get("terms") or []) + list(s.get("extra_terms") or []):
                    if t.get("category") != flag or t.get("excluded"):
                        continue
                    sp = t.get("span")
                    if not (isinstance(sp, list) and len(sp) == 2):
                        continue
                    stat["spans"] += 1
                    ok = 0 <= sp[0] < sp[1] <= len(text) and text[sp[0]:sp[1]].strip() != ""
                    if not ok:
                        stat["bad_span"] += 1
                    elif t.get("negated"):
                        negated = True
                    else:
                        valid = True
            if valid:
                stat["with_span"].append(flag)
            elif negated:
                stat["negated_only"].append(flag)
        out.append(stat)
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    rows = []
    for name in ("train_v3", "test_v3"):
        rows += [r for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high" and r["flags"].strip()]
    chunks = [rows[i::n * 4] for i in range(n * 4)]
    stats = []
    with mp.Pool(n) as pool:
        for part in pool.imap_unordered(work, chunks):
            stats += part
    summary = {f: {"raised": 0, "with_valid_span": 0, "no_span": 0, "negated_span_only": 0} for f in FLAGS}
    for s in stats:
        for f in s["raised"]:
            summary[f]["raised"] += 1
            if f in s["with_span"]: summary[f]["with_valid_span"] += 1
            elif f in s["negated_only"]: summary[f]["negated_span_only"] += 1
            else: summary[f]["no_span"] += 1
    total = {"reviews": len(stats), "spans_checked": sum(s["spans"] for s in stats), "invalid_spans": sum(s["bad_span"] for s in stats)}
    out = {"total": total, "per_flag": summary}
    (ROOT / "research" / "results").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / "research" / "results" / "evidence_check.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
