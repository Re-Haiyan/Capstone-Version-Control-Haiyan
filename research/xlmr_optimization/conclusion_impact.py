"""Effect of a candidate sentiment model on DeFaketive's product conclusions (real pipeline, real conclusion card, nothing saved).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/conclusion_impact.py labels hf:<checkpoint dir> <name> [products]     (labels every review once)
    backend/.venv/Scripts/python.exe research/xlmr_optimization/conclusion_impact.py impact <name> [products] [workers]          (real pipeline + conclusion card)

For the same saved products the shadow-sentiment study used (at least 60 written reviews; seed 11), the candidate labels every review once
(the model run in the main process on the unique texts), then the real analysis runs with the calibrator hook replaced, IN THIS PROCESS ONLY, by a lookup
of the candidate's label; the summary's `shadow_sentiment` block is then built with the same weights, and the conclusion card is built twice
(deployed fields and candidate block). Verdict states (issue warnings) are untouched. No production file, setting or database is changed.
Reports: decisions changed, direction, mean positive / neutral / negative shares, ranking agreement (Spearman) of the products by positive share,
and contradictions (a "recommended" conclusion on a product with an issue warning). It does NOT measure conclusion accuracy: no independently
labelled product-level judgments exist.
"""
import collections, copy, json, multiprocessing as mp, pathlib, random, sqlite3, sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis")); sys.path.insert(0, str(HERE))
LABELS = ("negative", "neutral", "positive")
_labels = {}


def init(table):
    global _labels
    _labels = table


def patched(text, stars, probabilities):
    label = _labels.get(str(text or ""))
    if label is None or not probabilities:
        return None
    return {"mode": "shadow", "calibrated": {"label": label, "probabilities": {k: (1.0 if k == label else 0.0) for k in LABELS}}}


def one(product):
    import dashboard_utils
    from defaketive_sentiment import hazard_model
    from defaketive_sentiment.analyze_reviews import analyze_product_json
    from defaketive_sentiment.registry import load_model
    hazard_model.calibrated_sentiment = patched
    analyzed = analyze_product_json([copy.deepcopy(product)], load_model())[0]
    summary = analyzed.get("sentiment_summary") or {}
    shadow = summary.get("shadow_sentiment")
    if not shadow or not dashboard_utils.is_badge_summary(summary):
        return {"link": product.get("link"), "skipped": True}
    base_view = dashboard_utils.badge_view(analyzed)
    variant = copy.deepcopy(analyzed)
    vs = variant["sentiment_summary"]
    vs["sentiment_counts"] = shadow["sentiment_counts"]; vs["positive_ratio_lower_bound"] = shadow["positive_ratio_lower_bound"]
    if "sentiment_shares" in shadow:
        vs["sentiment_shares"] = shadow["sentiment_shares"]
    cand_view = dashboard_utils.badge_view(variant)
    def shares(block):
        return block.get("sentiment_shares") or {k: v / max(sum(block["sentiment_counts"].values()), 1) for k, v in block["sentiment_counts"].items()}
    return {"link": product.get("link"), "name": (product.get("name") or "")[:60], "group": dashboard_utils.product_group(analyzed), "state": base_view["state"],
            "decision_deployed": (base_view.get("conclusion") or {}).get("decision"), "decision_candidate": (cand_view.get("conclusion") or {}).get("decision"),
            "pos_deployed": shares(summary).get("positive", 0.0), "pos_candidate": shares(shadow).get("positive", 0.0),
            "neu_deployed": shares(summary).get("uncertain", 0.0), "neu_candidate": shares(shadow).get("uncertain", 0.0),
            "neg_deployed": shares(summary).get("negative", 0.0), "neg_candidate": shares(shadow).get("negative", 0.0),
            "lb_deployed": summary.get("positive_ratio_lower_bound"), "lb_candidate": shadow["positive_ratio_lower_bound"]}


def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def sample_products(n_products):
    con = sqlite3.connect(f"file:{ROOT / 'backend' / 'defaketive.db'}?mode=ro", uri=True)
    products = []
    for raw, in con.execute("select raw_json from products where raw_json is not null"):
        p = json.loads(raw)
        if isinstance(p.get("comments"), list) and len(p["comments"]) >= 60 and isinstance(p.get("sentiment_summary"), dict):
            products.append(p)
    random.Random(11).shuffle(products)
    return products[:n_products]


if __name__ == "__main__":
    # stage 1 (training environment, has torch):  python conclusion_impact.py labels <model> <name> [products]
    # stage 2 (the app's own Python):             python conclusion_impact.py impact <name> [products] [workers]
    stage = sys.argv[1]
    if stage == "labels":
        model, name = sys.argv[2], sys.argv[3]
        products = sample_products(int(sys.argv[4]) if len(sys.argv) > 4 else 60)
        texts = sorted({str(c.get("content") or "") for p in products for c in p["comments"] if isinstance(c, dict)})
        print(f"{len(products)} products, {len(texts)} unique review texts to label with {model}", flush=True)
        import inference
        probs = inference.probs_hf(texts, inference.CARDIFF if model == "cardiff_fp32" else model[3:])
        json.dump({t: LABELS[int(p.argmax())] for t, p in zip(texts, probs)}, open(HERE / "results" / f"candidate_labels__{name}.json", "w"))
        sys.exit(0)
    name = sys.argv[2]
    model = name
    n_products = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    products = sample_products(n_products)
    table = json.load(open(HERE / "results" / f"candidate_labels__{name}.json"))
    with mp.Pool(workers, initializer=init, initargs=(table,)) as pool:
        results = [r for r in pool.imap_unordered(one, products) if r]
    done = [r for r in results if not r.get("skipped")]
    order = {"recommended": 3, "mixed": 2, "caution": 1, "not_recommended": 0}
    changed = [r for r in done if r["decision_deployed"] != r["decision_candidate"]]
    scaled = [r for r in changed if r["decision_deployed"] in order and r["decision_candidate"] in order]
    mean = lambda k: round(float(np.mean([r[k] for r in done])), 4)
    contradiction = lambda key: sum(1 for r in done if r["state"] != "no_warning_signs" and r[key] == "recommended")
    out = {"model": model, "name": name, "products_compared": len(done), "decisions_changed": len(changed),
           "more_favourable": sum(1 for r in scaled if order[r["decision_candidate"]] > order[r["decision_deployed"]]),
           "less_favourable": sum(1 for r in scaled if order[r["decision_candidate"]] < order[r["decision_deployed"]]),
           "mean_share": {"positive": [mean("pos_deployed"), mean("pos_candidate")], "neutral": [mean("neu_deployed"), mean("neu_candidate")], "negative": [mean("neg_deployed"), mean("neg_candidate")]},
           "decision_counts": {"deployed": dict(collections.Counter(r["decision_deployed"] for r in done)), "candidate": dict(collections.Counter(r["decision_candidate"] for r in done))},
           "transitions": {f"{a} -> {b}": v for (a, b), v in collections.Counter((r["decision_deployed"], r["decision_candidate"]) for r in changed).items()},
           "ranking_spearman_positive_share": round(spearman([r["pos_deployed"] for r in done], [r["pos_candidate"] for r in done]), 4),
           "ranking_spearman_lower_bound": round(spearman([r["lb_deployed"] for r in done], [r["lb_candidate"] for r in done]), 4),
           "recommended_despite_issue_warning": {"deployed": contradiction("decision_deployed"), "candidate": contradiction("decision_candidate")},
           "note": "behaviour change only; conclusion accuracy is not measured (no independently labelled conclusions exist)"}
    json.dump({"summary": out, "products": done}, open(HERE / "results" / f"conclusion_impact__{name}.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
