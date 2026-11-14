"""Effect of the evidence policy on real product verdicts and conclusion cards, and a check that shadow mode predicts it.

    backend\\.venv\\Scripts\\python.exe research\\shadow_evidence_policy.py <checkout_root> <out.json> [workers]
    (env COMPAT_DB=<sqlite file, opened read-only> and COMPAT_QUOTA="Lazada:12,Shopee:12" choose the products)

For each sampled saved product the real analysis runs twice from the same reviews: once with DEFAKETIVE_EVIDENCE_POLICY=shadow (the real
fields are the unchanged ones; the summary also carries `shadow_evidence_policy`) and once with =require (the policy actually applied).
Compared: verdict state, conclusion card, flag counts; and whether the shadow block equals what 'require' produced. Nothing is saved.
"""
import copy, json, multiprocessing as mp, os, pathlib, random, sqlite3, sys

DB = pathlib.Path(os.environ.get("COMPAT_DB") or pathlib.Path(__file__).resolve().parent.parent / "backend" / "defaketive.db")
_root = None


def init(root):
    global _root
    _root = pathlib.Path(root)
    for key in [k for k in os.environ if k.startswith("DEFAKETIVE_")]:
        del os.environ[key]
    sys.path.insert(0, str(_root / "backend")); sys.path.insert(0, str(_root / "backend" / "sentiment-analysis"))


def run_mode(product, mode):
    import dashboard_utils
    from defaketive_sentiment.analyze_reviews import analyze_product_json
    from defaketive_sentiment.registry import load_model
    os.environ["DEFAKETIVE_EVIDENCE_POLICY"] = mode
    analysed = analyze_product_json([copy.deepcopy(product)], load_model())[0]
    summary = analysed.get("sentiment_summary") or {}
    view = dashboard_utils.badge_view(analysed)
    return summary, view


def one(product):
    try:
        shadow_summary, shadow_view = run_mode(product, "shadow")
        require_summary, require_view = run_mode(product, "require")
    except Exception as error:  # noqa: BLE001
        return {"link": product.get("link"), "error": str(error)[:120]}
    block = shadow_summary.get("shadow_evidence_policy")
    flags = lambda s: {k: (v or {}).get("flagged_reviews") for k, v in (s.get("flags") or {}).items()}
    concl = lambda v: (v.get("conclusion") or {}).get("decision")
    return {"link": product.get("link"), "platform": product.get("platform"), "name": (product.get("name") or "")[:50], "comments": len(product.get("comments") or []),
            "state_keep": (shadow_summary.get("verdict") or {}).get("state"), "state_require": (require_summary.get("verdict") or {}).get("state"),
            "decision_keep": concl(shadow_view), "decision_require": concl(require_view),
            "flags_keep": flags(shadow_summary), "flags_require": flags(require_summary),
            "safety_keep": (shadow_summary.get("safety") or {}).get("flagged_reviews"), "safety_require": (require_summary.get("safety") or {}).get("flagged_reviews"),
            "had_something_to_drop": bool(block), "shadow_state": (block or {}).get("verdict_state"), "shadow_flags": (block or {}).get("flagged_reviews"),
            "dropped": (block or {}).get("dropped_flags")}


if __name__ == "__main__":
    root, dst = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True); products = []
    for raw, platform in con.execute("select raw_json, platform from products where raw_json is not null"):
        p = json.loads(raw)
        if isinstance(p.get("comments"), list) and len(p["comments"]) >= 40:
            products.append((platform, p))
    random.Random(31).shuffle(products)
    quota = {}
    for part in (os.environ.get("COMPAT_QUOTA") or "Lazada:60").split(","):
        quota[part.split(":")[0].strip()] = int(part.split(":")[1])
    sample = []
    for name, count in quota.items():
        sample += [p for pl, p in products if name.lower() in pl.lower()][:count]
    with mp.Pool(workers, initializer=init, initargs=(root,)) as pool:
        results = list(pool.imap_unordered(one, sample))
    ok = [r for r in results if "error" not in r]
    changed_state = [r for r in ok if r["state_keep"] != r["state_require"]]
    changed_decision = [r for r in ok if r["decision_keep"] != r["decision_require"]]
    touched = [r for r in ok if r["had_something_to_drop"]]
    consistent = [r for r in touched if r["shadow_state"] == r["state_require"] and r["shadow_flags"] == {k: v for k, v in r["flags_require"].items() if k in (r["shadow_flags"] or {})}]
    safety_changed = [r for r in ok if r["safety_keep"] != r["safety_require"]]
    summary = {"products": len(ok), "errors": len(results) - len(ok), "platforms": {pl: sum(1 for r in ok if r["platform"] == pl) for pl in {r["platform"] for r in ok}},
               "products_with_something_to_drop": len(touched), "verdict_state_changed": len(changed_state), "conclusion_card_changed": len(changed_decision),
               "shadow_block_equals_the_require_result": f"{len(consistent)} of {len(touched)}", "safety_counts_changed": len(safety_changed),
               "state_transitions": {f"{a} -> {b}": sum(1 for r in changed_state if (r['state_keep'], r['state_require']) == (a, b)) for a, b in {(r['state_keep'], r['state_require']) for r in changed_state}},
               "decision_transitions": {f"{a} -> {b}": sum(1 for r in changed_decision if (r['decision_keep'], r['decision_require']) == (a, b)) for a, b in {(r['decision_keep'], r['decision_require']) for r in changed_decision}},
               "defect_flagged_reviews_total": [sum((r["flags_keep"].get("defect") or 0) for r in ok), sum((r["flags_require"].get("defect") or 0) for r in ok)]}
    json.dump({"summary": summary, "products": ok}, open(dst, "w"), indent=1)
    print(json.dumps(summary, indent=1))
