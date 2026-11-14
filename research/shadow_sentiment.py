"""Shadow-mode evaluation of the sentiment calibrator on SAVED products (the real pipeline, real conclusion card).

    backend\\.venv\\Scripts\\python.exe research\\shadow_sentiment.py [products] [workers]

For each sampled saved product the real analysis runs with DEFAKETIVE_SENTIMENT_CALIBRATOR set in shadow mode. The summary then
holds the real sentiment fields and a `shadow_sentiment` block computed from the calibrated labels with the same weights.
The conclusion card (`dashboard_utils.badge_view`) is built twice: from the real fields and from the shadow block, and the
decisions, positive shares and neutral shares are compared. Nothing is saved to the database; no live setting changes.
Writes research/results/shadow_sentiment.json.
"""
import collections, copy, json, multiprocessing as mp, os, pathlib, random, sqlite3, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
ARTIFACT = ROOT / "research" / "artifacts" / "sentiment_calibrator_v1.joblib"


def one(product):
    os.environ["DEFAKETIVE_SENTIMENT_CALIBRATOR"] = str(ARTIFACT)
    os.environ["DEFAKETIVE_SENTIMENT_CALIBRATOR_MODE"] = "shadow"
    import dashboard_utils
    from defaketive_sentiment.analyze_reviews import analyze_product_json
    from defaketive_sentiment.registry import load_model
    analyzed = analyze_product_json([copy.deepcopy(product)], load_model())[0]
    summary = analyzed.get("sentiment_summary") or {}
    shadow = summary.get("shadow_sentiment")
    if not shadow or not dashboard_utils.is_badge_summary(summary):
        return {"link": product.get("link"), "skipped": "no shadow block or not a badge summary"}
    base_view = dashboard_utils.badge_view(analyzed)
    variant = copy.deepcopy(analyzed); vs = variant["sentiment_summary"]
    vs["sentiment_counts"] = shadow["sentiment_counts"]; vs["positive_ratio_lower_bound"] = shadow["positive_ratio_lower_bound"]
    if "sentiment_shares" in shadow:
        vs["sentiment_shares"] = shadow["sentiment_shares"]
    shadow_view = dashboard_utils.badge_view(variant)
    shares = lambda s, block: (block.get("sentiment_shares") or {k: v / max(sum(block["sentiment_counts"].values()), 1) for k, v in block["sentiment_counts"].items()})
    return {"link": product.get("link"), "name": (product.get("name") or "")[:60], "group": dashboard_utils.product_group(analyzed), "usable": base_view["reviews_analyzed"],
            "state": base_view["state"], "weighted": bool(summary.get("weighted")),
            "decision_deployed": (base_view.get("conclusion") or {}).get("decision"), "decision_calibrated": (shadow_view.get("conclusion") or {}).get("decision"),
            "positive_deployed": round(shares(summary, summary).get("positive", 0.0), 4), "positive_calibrated": round(shares(summary, shadow).get("positive", 0.0), 4),
            "neutral_deployed": round(shares(summary, summary).get("uncertain", 0.0), 4), "neutral_calibrated": round(shares(summary, shadow).get("uncertain", 0.0), 4),
            "negative_deployed": round(shares(summary, summary).get("negative", 0.0), 4), "negative_calibrated": round(shares(summary, shadow).get("negative", 0.0), 4),
            "lower_bound_deployed": summary.get("positive_ratio_lower_bound"), "lower_bound_calibrated": shadow["positive_ratio_lower_bound"]}


if __name__ == "__main__":
    n_products = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    con = sqlite3.connect(str(ROOT / "backend" / "defaketive.db"))
    products = []
    for raw, in con.execute("select raw_json from products where raw_json is not null"):
        p = json.loads(raw)
        if isinstance(p.get("comments"), list) and len(p["comments"]) >= 60 and isinstance(p.get("sentiment_summary"), dict):
            products.append(p)
    random.Random(11).shuffle(products)
    products = products[:n_products]
    print(f"{len(products)} saved products sampled (of those with at least 60 written reviews)", flush=True)
    with mp.Pool(workers) as pool:
        results = [r for r in pool.imap_unordered(one, products) if r]
    done = [r for r in results if "skipped" not in r]
    order = {"recommended": 3, "mixed": 2, "caution": 1, "not_recommended": 0}  # "not_enough" has no place on the favourability scale
    trans = collections.Counter((r["decision_deployed"], r["decision_calibrated"]) for r in done)
    changed = [r for r in done if r["decision_deployed"] != r["decision_calibrated"]]
    scaled = [r for r in changed if r["decision_deployed"] in order and r["decision_calibrated"] in order]
    better = [r for r in scaled if order[r["decision_calibrated"]] > order[r["decision_deployed"]]]
    worse = [r for r in scaled if order[r["decision_calibrated"]] < order[r["decision_deployed"]]]
    mean = lambda k: round(sum(r[k] for r in done) / max(len(done), 1), 4)
    by_group = collections.defaultdict(list)
    for r in done: by_group[r["group"]].append(r)
    summary = {"products_compared": len(done), "skipped": len(results) - len(done), "decisions_changed": len(changed), "more_favourable": len(better), "less_favourable": len(worse), "changed_to_or_from_not_enough": len(changed) - len(scaled),
               "mean_shares": {"positive": [mean("positive_deployed"), mean("positive_calibrated")], "neutral": [mean("neutral_deployed"), mean("neutral_calibrated")], "negative": [mean("negative_deployed"), mean("negative_calibrated")]},
               "transitions_deployed_to_calibrated": {f"{a} -> {b}": v for (a, b), v in sorted(trans.items(), key=lambda kv: -kv[1])},
               "decision_counts": {"deployed": dict(collections.Counter(r["decision_deployed"] for r in done)), "calibrated": dict(collections.Counter(r["decision_calibrated"] for r in done))},
               "by_group": {g: {"products": len(v), "changed": sum(1 for r in v if r["decision_deployed"] != r["decision_calibrated"]), "mean_positive": [round(sum(r["positive_deployed"] for r in v) / len(v), 3), round(sum(r["positive_calibrated"] for r in v) / len(v), 3)]} for g, v in by_group.items()},
               "verdict_states_untouched": True}
    json.dump({"summary": summary, "products": done}, open(ROOT / "research" / "results" / "shadow_sentiment.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))
