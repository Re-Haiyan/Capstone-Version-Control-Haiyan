"""Blank sheets for independently judging product conclusions (the five cards), plus the scoring once they are filled.

    backend\\.venv\\Scripts\\python.exe research\\conclusion_eval.py make [products]
    backend\\.venv\\Scripts\\python.exe research\\conclusion_eval.py score sheetA_done.csv sheetB_done.csv

`make` samples saved products, stratified by the conclusion the system currently shows (so rare conclusions are covered),
and writes to research/conclusion_eval/: product_sheet_A.csv and product_sheet_B.csv (the same products under anonymous ids,
different order, empty judgement columns), product_reviews.csv (what each annotator reads per product), and manifest_private.csv
(the system's conclusion per product: keep it from the annotators). The sheets show no system output.
`score` compares each annotator with the system (accuracy, weighted kappa, error distance, the dangerous error of reassuring on a
product both annotators found seriously unsafe) and the two annotators with each other. It refuses to run without 30 products
judged by both annotators. Nothing is invented: with no filled sheets there are no results.
"""
import collections, csv, json, pathlib, random, sqlite3, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
OUT = ROOT / "research" / "conclusion_eval"
CARDS = ("Well reviewed", "Mixed reviews", "Some concerns", "Not recommended", "Too few reviews")
SYSTEM_TO_CARD = {"recommended": "Well reviewed", "mixed": "Mixed reviews", "caution": "Some concerns", "not_recommended": "Not recommended", "not_enough": "Too few reviews", None: "Too few reviews"}
SEVERITY = {"Well reviewed": 0, "Mixed reviews": 1, "Some concerns": 2, "Not recommended": 3}
PROBLEM_WORDS = ("sira", "basag", "peke", "fake", "scam", "usok", "sunog", "umiinit", "overheat", "rash", "allerg", "expired", "panis", "mali", "kulang", "hindi gumana", "not working", "broken", "defect", "leak", "burn", "smoke", "spark", "wrong", "damaged")
SHEET_COLS = ["product_id", "platform", "name", "listed_rating", "listed_star_percent", "reviews_in_file", "conclusion", "serious_safety_concern", "counterfeit_concern", "main_reason", "confidence"]


def make(n_products: int = 100, seed: int = 7):
    import dashboard_utils
    OUT.mkdir(exist_ok=True)
    rng = random.Random(seed)
    con = sqlite3.connect(str(ROOT / "backend" / "defaketive.db"))
    products = []
    for raw, in con.execute("select raw_json from products where raw_json is not null"):
        p = json.loads(raw)
        if isinstance(p.get("comments"), list) and p["comments"] and isinstance(p.get("sentiment_summary"), dict) and dashboard_utils.is_badge_summary(p["sentiment_summary"]):
            view = dashboard_utils.badge_view(p)
            p["_system"] = SYSTEM_TO_CARD.get((view.get("conclusion") or {}).get("decision")) if (view.get("conclusion")) else "Too few reviews"
            products.append(p)
    by = collections.defaultdict(list)
    for p in products:
        by[p["_system"]].append(p)
    for v in by.values():
        rng.shuffle(v)
    chosen, quota = [], max(n_products // len(CARDS), 1)
    for card in CARDS:
        chosen += by.get(card, [])[:quota]
    rest = [p for p in products if p not in chosen]; rng.shuffle(rest)
    chosen += rest[: max(n_products - len(chosen), 0)]
    rng.shuffle(chosen)
    reviews_rows, manifest, sheet = [], [], []
    for n, p in enumerate(chosen, start=1):
        pid = f"P{n:03d}"
        comments = [c for c in p["comments"] if isinstance(c, dict) and str(c.get("content") or "").strip()]
        listed = p.get("review_star_distribution") or {}
        total = sum(float(v or 0) for v in listed.values()) if isinstance(listed, dict) else 0
        pct = "; ".join(f"{s}-star {round(100 * float(listed.get(str(s)) or 0) / total)}%" for s in range(5, 0, -1)) if total else "not available"
        # a representative sample (random) plus up to 10 reviews a plain word list says may describe a problem (no system output used)
        sample = rng.sample(comments, min(30, len(comments)))
        flagged = [c for c in comments if any(w in str(c["content"]).casefold() for w in PROBLEM_WORDS) and c not in sample]
        picked = [("sample", c) for c in sample] + [("possible problem", c) for c in rng.sample(flagged, min(10, len(flagged)))]
        rng.shuffle(picked)
        for kind, c in picked:
            reviews_rows.append({"product_id": pid, "stars": c.get("rating"), "review": " ".join(str(c["content"]).split())[:600]})
        sheet.append({"product_id": pid, "platform": p.get("platform") or "", "name": " ".join((p.get("name") or "").split())[:110], "listed_rating": p.get("rating") or "",
                      "listed_star_percent": pct, "reviews_in_file": len(picked), "conclusion": "", "serious_safety_concern": "", "counterfeit_concern": "", "main_reason": "", "confidence": ""})
        manifest.append({"product_id": pid, "link": p.get("link"), "system_conclusion": p["_system"], "reviews_available": len(comments)})
    for name, order_seed in (("A", 1), ("B", 2)):
        rows = sheet[:]; random.Random(order_seed).shuffle(rows)
        with open(OUT / f"product_sheet_{name}.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=SHEET_COLS); w.writeheader(); w.writerows(rows)
    with open(OUT / "product_reviews.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["product_id", "stars", "review"]); w.writeheader(); w.writerows(reviews_rows)
    with open(OUT / "manifest_private.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["product_id", "link", "system_conclusion", "reviews_available"]); w.writeheader(); w.writerows(manifest)
    print(f"{len(chosen)} products; system conclusions in the sample: {dict(collections.Counter(m['system_conclusion'] for m in manifest))}")


def weighted_kappa(a, b, k=4):
    """Quadratic-weighted kappa on the four ordered cards (Well reviewed .. Not recommended)."""
    import numpy as np
    n = np.zeros((k, k))
    for x, y in zip(a, b):
        n[x, y] += 1
    w = np.array([[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)])
    e = np.outer(n.sum(1), n.sum(0)) / n.sum()
    return float(1 - (w * n).sum() / (w * e).sum()) if (w * e).sum() else float("nan")


def score(path_a, path_b):
    read = lambda p: {r["product_id"]: r for r in csv.DictReader(open(p, encoding="utf-8-sig"))}
    A, B = read(path_a), read(path_b)
    manifest = {r["product_id"]: r for r in csv.DictReader(open(OUT / "manifest_private.csv", encoding="utf-8-sig"))}
    ok = lambda r: bool(r and r.get("conclusion", "").strip() in CARDS)
    ids = [i for i in A if i in B and i in manifest and ok(A[i]) and ok(B[i])]
    if len(ids) < 30:
        sys.exit(f"Only {len(ids)} products are judged by both annotators; at least 30 are needed.")
    print(f"{len(ids)} products judged by both annotators")
    agree = sum(A[i]["conclusion"] == B[i]["conclusion"] for i in ids) / len(ids)
    print(f"annotator A vs B: exact agreement {agree:.3f}")
    ordered = [i for i in ids if A[i]["conclusion"] in SEVERITY and B[i]["conclusion"] in SEVERITY]
    if ordered:
        print(f"annotator A vs B: quadratic-weighted kappa {weighted_kappa([SEVERITY[A[i]['conclusion']] for i in ordered], [SEVERITY[B[i]['conclusion']] for i in ordered]):.3f}  (on {len(ordered)} products both put on the four-step scale)")
    for name, S in (("A", A), ("B", B)):
        match = sum(S[i]["conclusion"] == manifest[i]["system_conclusion"] for i in ids) / len(ids)
        steps = collections.Counter(abs(SEVERITY.get(S[i]["conclusion"], 0) - SEVERITY.get(manifest[i]["system_conclusion"], 0)) for i in ids if S[i]["conclusion"] in SEVERITY and manifest[i]["system_conclusion"] in SEVERITY)
        print(f"annotator {name} vs system: exact {match:.3f}; steps apart {dict(sorted(steps.items()))}")
    both_match = sum(A[i]["conclusion"] == B[i]["conclusion"] == manifest[i]["system_conclusion"] for i in ids)
    agreed = [i for i in ids if A[i]["conclusion"] == B[i]["conclusion"]]
    print(f"system matches the annotators when they agree: {sum(A[i]['conclusion'] == manifest[i]['system_conclusion'] for i in agreed)} of {len(agreed)}")
    unsafe = [i for i in ids if A[i]["serious_safety_concern"].strip().lower() == "yes" and B[i]["serious_safety_concern"].strip().lower() == "yes"]
    reassured = [i for i in unsafe if manifest[i]["system_conclusion"] in ("Well reviewed", "Mixed reviews")]
    print(f"dangerous false reassurance: {len(reassured)} of {len(unsafe)} products both annotators found seriously unsafe were shown as Well reviewed or Mixed reviews")
    print(f"all three agree exactly on {both_match} of {len(ids)} products")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "make":
        make(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    elif len(sys.argv) == 4 and sys.argv[1] == "score":
        score(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
