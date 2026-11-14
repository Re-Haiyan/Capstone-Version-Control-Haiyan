"""Prepare a proposed FRESH, product-disjoint evaluation set (blank annotation sheet + split manifest). No labels are created.

    D:\\defaketive-train\\Scripts\\python.exe research\\fresh_eval.py <vm_reviews.json>

Eligible products: reviews exist in the pool, at least 30 of them, and the product appears in NO labelled, pooled or
previously inspected file (evaluation/**). Roles, kept apart in the manifest and not shown on the sheet:
  representative   up to 8 reviews drawn uniformly at random per eligible product. These carry sampling weights
                   (listing star mix over the pool star mix, times pool size over sample size) so weighted metrics estimate
                   the reviews of these products, because the scanner reads a fixed number of reviews per star level.
  enrichment       reviews with a hazard, fake or mismatch word from the same products, for the rare flags. NOT a
                   representative sample: never quote its scores as marketplace performance.
  al_candidate     the active-learning training candidates whose product is not among the eligible products (the others are
                   dropped so that training candidates and the test never share a product).
All three are annotated blind from one sheet with anonymous ids.
"""
import collections, csv, glob, hashlib, json, pathlib, random, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import product_category as pc  # noqa: E402

OUT = ROOT / "research" / "fresh_eval"; OUT.mkdir(exist_ok=True)
norm_p = lambda p: " ".join(p.split())
norm_t = lambda t: re.sub(r"\W+", " ", t.casefold()).strip()
rng = random.Random(20261114)

seen_products, used_text = set(), set()
for f in glob.glob(str(ROOT / "evaluation" / "**" / "*.csv"), recursive=True):
    if f.endswith("_key.csv"):
        continue
    try:
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r.get("product"):
                seen_products.add(norm_p(r["product"]))
            if r.get("review_text"):
                used_text.add(norm_t(r["review_text"]))
    except Exception:
        pass

pool = collections.defaultdict(list)
for name, rating, text in json.load(open(sys.argv[1], encoding="utf-8")):
    text = " ".join((text or "").split())
    if rating is None or not (20 <= len(text) <= 500) or norm_t(text) in used_text:
        continue
    pool[norm_p(name)].append({"stars": int(rating), "text": text})
dist = json.load(open(ROOT / "research/cache/unseen_star_distribution.json", encoding="utf-8"))
eligible = sorted(p for p in pool if p not in seen_products and len(pool[p]) >= 30 and p in dist and dist[p].get("review_star_distribution"))
print(f"eligible products: {len(eligible)}; groups: {dict(collections.Counter(pc.group_of(pc.classify_listing({'name': p})) for p in eligible))}")

HAZ = re.compile(r"usok|umusok|smok|sunog|nasunog|burn|sumabog|pumutok|spark|nakuryente|uminit|umiinit|overheat|bloat|namaga|rash|allerg|fake|peke|not original|hindi original|imitation|scam|wrong|mali ang|kulang|missing|iba ang|different from|not as described", re.I)
rows, weight = [], {}
for p in eligible:
    reviews = pool[p][:]; rng.shuffle(reviews)
    sample = reviews[:8]; rest = reviews[8:]
    listed = {int(k): float(v) for k, v in (dist[p]["review_star_distribution"] or {}).items() if str(k).isdigit()}
    in_pool = collections.Counter(r["stars"] for r in pool[p])
    for r in sample:
        w_star = (max(listed.get(r["stars"], 0.0), 1.0) / in_pool[r["stars"]]) if in_pool[r["stars"]] and listed else 1.0  # a star level that exists in the pool never gets weight 0, even if the listing reports none
        rows.append({"product": p, "stars": r["stars"], "text": r["text"], "role": "representative", "sampling_weight": round(w_star * len(pool[p]) / len(sample), 4)})
    hazard = [r for r in rest if HAZ.search(r["text"])]
    for r in hazard[:3]:
        rows.append({"product": p, "stars": r["stars"], "text": r["text"], "role": "enrichment", "sampling_weight": ""})
enrich = [r for r in rows if r["role"] == "enrichment"]
if len(enrich) > 150:
    keep = set(map(id, rng.sample(enrich, 150))); rows = [r for r in rows if r["role"] != "enrichment" or id(r) in keep]

# active-learning candidates that do not share a product with the eligible (test) products
al = list(csv.DictReader(open(ROOT / "research/active_learning_candidates.csv", encoding="utf-8-sig")))
test_products = set(eligible); kept_al = [a for a in al if norm_p(a["product"]) not in test_products]
for a in kept_al:
    rows.append({"product": norm_p(a["product"]), "stars": "", "text": a["review_text"], "role": "al_candidate", "sampling_weight": ""})
with open(OUT / "active_learning_candidates_disjoint.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(al[0].keys())); w.writeheader(); w.writerows(kept_al)

rng.shuffle(rows)
for n, r in enumerate(rows, start=1):
    r["sheet_id"] = f"F{n:04d}"
with open(OUT / "fresh_eval_sheet.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh); w.writerow(["id", "stars", "product", "review_text", "sentiment", "flags", "confidence"])
    for r in rows:
        w.writerow([r["sheet_id"], r["stars"], r["product"], r["text"], "", "", ""])
with open(OUT / "split_manifest.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh); w.writerow(["sheet_id", "role", "product", "group", "stars", "sampling_weight", "text_sha1"])
    for r in sorted(rows, key=lambda r: r["sheet_id"]):
        w.writerow([r["sheet_id"], r["role"], r["product"], pc.group_of(pc.classify_listing({"name": r["product"]})), r["stars"], r["sampling_weight"], hashlib.sha1(r["text"].encode("utf-8")).hexdigest()[:12]])
c = collections.Counter(r["role"] for r in rows)
summary = {"eligible_products": len(eligible), "roles": dict(c), "active_learning_candidates_in": len(al), "active_learning_candidates_dropped_for_sharing_a_product": len(al) - len(kept_al),
           "groups_of_eligible_products": dict(collections.Counter(pc.group_of(pc.classify_listing({"name": p})) for p in eligible)),
           "products_in_any_earlier_labelled_or_inspected_file": len(seen_products)}
json.dump(summary, open(ROOT / "research/results/fresh_eval_summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
