"""API-shape and product-aggregation check of ANY checkout, on real saved products, with every experimental switch cleared.

    backend\\.venv\\Scripts\\python.exe research\\api_compat.py <checkout_root> <out.json> [products]

Runs the same path the app uses (dashboard_utils.analyze_products, then with_badge_view / badge_view, which the /api/products,
/api/products/detail and /api/upload routes serve) on a fixed sample of saved Lazada and Temu products. Records the full set of
key paths in each result (so two checkouts can be compared for removed or added keys) and the verdict, state, decision and counts
per product (so aggregation can be compared). Nothing is saved to the database.
"""
import copy, json, os, pathlib, random, sqlite3, sys

DB = pathlib.Path(os.environ.get("COMPAT_DB") or pathlib.Path(__file__).resolve().parent.parent / "backend" / "defaketive.db")  # COMPAT_DB: another database, opened read-only
root = pathlib.Path(sys.argv[1]); dst = sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
for key in [k for k in os.environ if k.startswith("DEFAKETIVE_")]:
    del os.environ[key]
sys.path.insert(0, str(root / "backend")); sys.path.insert(0, str(root / "backend" / "sentiment-analysis"))
import dashboard_utils  # noqa: E402


def paths(value, prefix=""):
    found = set()
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "comments":
                continue
            found.add(f"{prefix}/{k}")
            found |= paths(v, f"{prefix}/{k}")
    elif isinstance(value, list) and value:
        for item in value[:3]:
            found |= paths(item, prefix + "[]")
    return found


con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
products = []
for raw, platform in con.execute("select raw_json, platform from products where raw_json is not null"):
    p = json.loads(raw)
    if isinstance(p.get("comments"), list) and len(p["comments"]) >= 40:
        products.append((platform, p))
random.Random(21).shuffle(products)
quota = {}
for part in (os.environ.get("COMPAT_QUOTA") or "").split(","):
    if ":" in part:
        quota[part.split(":")[0].strip()] = int(part.split(":")[1])
if quota:  # e.g. COMPAT_QUOTA="Lazada:6,Shopee:6"
    sample = []
    for name, count in quota.items():
        sample += [p for pl, p in products if name.lower() in pl.lower()][:count]
else:
    lazada = [p for pl, p in products if "Lazada" in pl][: n - 2]; other = [p for pl, p in products if "Lazada" not in pl][:2]
    sample = lazada + other
analysed = dashboard_utils.analyze_products(sample)
out = {"root": str(root), "products": [], "key_paths": {"card": [], "view": [], "summary": []}}
card_paths, view_paths, summary_paths = set(), set(), set()
for before, product in zip(sample, analysed):
    card = {k: v for k, v in dashboard_utils.with_badge_view(product).items() if k != "comments"}
    view = dashboard_utils.badge_view(product)
    summary = product.get("sentiment_summary") or {}
    card_paths |= paths(card); view_paths |= paths(view); summary_paths |= paths(summary)
    concl = view.get("conclusion") or {}
    out["products"].append({"link": before.get("link"), "platform": before.get("platform"), "name": (before.get("name") or "")[:50], "n_comments": len(before.get("comments") or []), "state": view.get("state"), "decision": concl.get("decision"), "assessment": concl.get("assessment"),
                            "reviews_analyzed": view.get("reviews_analyzed"), "counts": view.get("counts"), "positive_lb": summary.get("positive_ratio_lower_bound"),
                            "sentiment_counts": summary.get("sentiment_counts")})
out["key_paths"] = {"card": sorted(card_paths), "view": sorted(view_paths), "summary": sorted(summary_paths)}
json.dump(out, open(dst, "w"), indent=1)
print(len(sample), "products;", {k: len(v) for k, v in out["key_paths"].items()}, "key paths")
