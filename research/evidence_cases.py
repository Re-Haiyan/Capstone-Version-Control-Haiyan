"""Which flags have no highlighted words, and why? (uses the deployed checker's review_evidence field)

    backend\.venv\Scripts\python.exe research\evidence_cases.py [workers]

For every flag raised on the labelled reviews, records the evidence state (keyword_span / listing_context / model_only),
the layer that raised it (keyword layer or extra-label layer) and the sentence text. Writes research/results/evidence_cases.json
and research/evidence_cases.csv (the model-only cases, for manual judgement).
"""
import collections, csv, json, multiprocessing as mp, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
_model = None


def work(rows):
    global _model
    if _model is None:
        from defaketive_sentiment import registry
        _model = registry.load_model()
    out = []
    for r in rows:
        a = _model.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]})[0]
        for flag, e in a["review_evidence"].items():
            sent = a["sentences"]
            layers = set()
            for i in e["sentences"]:
                s = next((x for x in sent if int(x.get("index", -1)) == i), None)
                if s is None:
                    continue
                if flag in (s.get("tags") or ()): layers.add("keyword_or_learned_layer")
                if flag in (s.get("extra_tags") or ()): layers.add("extra_label_layer")
            quote = " | ".join(next((x["text_raw"] for x in sent if int(x.get("index", -1)) == i), "") for i in e["sentences"])
            out.append({"id": r["id"], "flag": flag, "state": e["state"], "layers": sorted(layers), "spans": len(e["spans"]), "quote": quote[:240], "model_score": e.get("model_score"),
                        "valid_offsets": all(sp["review_start"] is not None and a["review_excerpt"] is not None for sp in e["spans"])})
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    rows = []
    for name in ("train_v3", "test_v3"):
        rows += [dict(r, split=name) for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high" and r["flags"].strip()]
    res = []
    with mp.Pool(n) as pool:
        for part in pool.imap_unordered(work, [rows[i::n * 4] for i in range(n * 4)]):
            res += part
    by = collections.defaultdict(collections.Counter)
    for x in res:
        by[x["flag"]][x["state"]] += 1
    layer = collections.defaultdict(collections.Counter)
    for x in res:
        if x["state"] != "keyword_span":
            layer[(x["flag"], x["state"])][",".join(x["layers"])] += 1
    summary = {f: dict(c) for f, c in by.items()}
    json.dump({"reviews": len(rows), "flags_raised": len(res), "by_flag_state": summary, "no_span_by_layer": {f"{k[0]}|{k[1]}": dict(v) for k, v in layer.items()}}, open(ROOT / "research/results/evidence_cases.json", "w"), indent=1)
    json.dump([{"id": x["id"], "flag": x["flag"], "state": x["state"]} for x in res], open(ROOT / "research/results/evidence_states.json", "w"))
    mo = [x for x in res if x["state"] == "model_only"]
    with open(ROOT / "research/evidence_cases.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "flag", "state", "layers", "model_score", "quote"]); w.writeheader()
        for x in sorted(mo, key=lambda x: (x["flag"], x["id"])):
            w.writerow({"id": x["id"], "flag": x["flag"], "state": x["state"], "layers": ",".join(x["layers"]), "model_score": x["model_score"], "quote": x["quote"]})
    print(json.dumps(summary, indent=1)); print("no-span by layer:", {f"{k[0]}|{k[1]}": dict(v) for k, v in layer.items()})
