"""Build the fresh, product-disjoint annotation material for the sentiment study from a copy of the production database (read only).

    backend/.venv/Scripts/python.exe research/xlmr_optimization/build_annotation_sheets.py <defaketive.db copy>

Writes research/xlmr_optimization/annotation/:
  final_test_sheet_A.csv, final_test_sheet_B.csv   the SAME 400 reviews for two independent annotators, anonymous ids (T001..T400), shuffled
                                                   differently, empty label columns. Shown: product title, category group, platform, language hint,
                                                   review text. NOT shown: star rating, any model output, any existing label, the split.
  dev_pool_sheet.csv                               400 further reviews (other products) to label for training and validation later.
  PRIVATE_id_map.csv                               sheet id -> review key, product link, stars, group, split, sampling weight. KEEP FROM ANNOTATORS.
  frozen_final_test.json                           the frozen list's SHA-256 and the sampling plan: the final test is fixed BEFORE any model is chosen.
Rules: a product belongs to exactly one of final_test / dev_pool (decided by a hash of its link); products whose title appears in any
team-labelled file are excluded from both; texts are deduplicated; at most 6 reviews per product; stratified by star group and by category
group because the natural distribution is almost all five-star electronics (weights are recorded so a score can be re-weighted).
Nothing here is a human label. No annotation field is filled.
"""
import csv, hashlib, json, pathlib, random, re, sqlite3, sys, datetime

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
sys.path.insert(0, str(HERE))
from defaketive_sentiment import product_category as pc  # noqa: E402
import xdata, metrics_x  # noqa: E402

OUT = HERE / "annotation"
OUT.mkdir(exist_ok=True)
N_TEST, N_DEV, PER_PRODUCT = 400, 400, 6
# target share of each part by category group (what the production database can actually supply is limited; see the plan file)
GROUP_QUOTA = {"electronics": 0.40, "home_living": 0.15, "fashion": 0.12, "beauty_health": 0.10, "food_grocery": 0.08, "automotive_tools": 0.08, "other": 0.07}
STAR_QUOTA = {"1-2": 0.30, "3": 0.20, "4": 0.20, "5": 0.30}


def star_bucket(s):
    return "1-2" if s <= 2 else str(s)


def main(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    products = {link: (name, plat) for link, name, plat in con.execute("SELECT link, name, platform FROM products")}
    labelled = set()
    for rows in xdata.load_marketplace().values():
        labelled |= {" ".join(r["product"].lower().split()) for r in rows if r["product"]}
    group = {l: pc.group_of(pc.classify_listing({"name": n})) for l, (n, _) in products.items()}
    group = {l: (g if g in GROUP_QUOTA else "other") for l, g in group.items()}
    side = {l: ("final_test" if int(hashlib.sha256(l.encode()).hexdigest(), 16) % 2 == 0 else "dev_pool") for l in products}
    rng = random.Random(20261115)
    seen_text, pool = set(), []
    allrows = con.execute("SELECT review_key, product_link, rating, content FROM reviews WHERE length(content) >= 12").fetchall()
    rng.shuffle(allrows)
    per = {}
    excluded_products = set()
    for key, link, rating, content in allrows:
        name = " ".join(products.get(link, ("", ""))[0].lower().split())
        if link not in products or name in labelled:
            excluded_products.add(link)
            continue
        nt = xdata.norm_text(content)
        if len(nt.split()) < 2 or nt in seen_text or rating is None:
            continue
        if per.get(link, 0) >= PER_PER_PRODUCT_LIMIT(side[link]):
            continue
        seen_text.add(nt)
        per[link] = per.get(link, 0) + 1
        pool.append({"key": key, "link": link, "stars": int(rating), "text": content.strip(), "group": group[link], "side": side[link], "platform": products[link][1], "product": products[link][0]})
    chosen = {"final_test": [], "dev_pool": []}
    plan = {"available_after_filters": {}, "chosen": {}}
    for part, n in (("final_test", N_TEST), ("dev_pool", N_DEV)):
        avail = [r for r in pool if r["side"] == part]
        plan["available_after_filters"][part] = {"reviews": len(avail), "products": len({r["link"] for r in avail}),
                                                 "by_group": {g: sum(r["group"] == g for r in avail) for g in GROUP_QUOTA}, "by_star": {s: sum(star_bucket(r["stars"]) == s for r in avail) for s in STAR_QUOTA}}
        picked, used = [], set()
        for g, gq in GROUP_QUOTA.items():
            for sb, sq in STAR_QUOTA.items():
                cell = [r for r in avail if r["group"] == g and star_bucket(r["stars"]) == sb and r["key"] not in used]
                rng.shuffle(cell)
                take = cell[: round(n * gq * sq)]
                picked += take
                used |= {r["key"] for r in take}
        shortfall = n - len(picked)
        rest = [r for r in avail if r["key"] not in used]
        rng.shuffle(rest)
        picked += rest[:max(0, shortfall)]
        chosen[part] = picked[:n]
        plan["chosen"][part] = {"reviews": len(chosen[part]), "products": len({r["link"] for r in chosen[part]}), "filled_outside_quota": max(0, shortfall),
                                "by_group": {g: sum(r["group"] == g for r in chosen[part]) for g in GROUP_QUOTA}, "by_platform": {p: sum(r["platform"] == p for r in chosen[part]) for p in sorted({r["platform"] for r in chosen[part]})},
                                "by_star": {s: sum(star_bucket(r["stars"]) == s for r in chosen[part]) for s in STAR_QUOTA}}
    assert not ({r["link"] for r in chosen["final_test"]} & {r["link"] for r in chosen["dev_pool"]}), "a product is on both sides"
    # sampling weights: natural share of (group x star) among eligible reviews divided by sampled share, so a re-weighted score reflects the eligible population
    elig = [r for r in pool if r["side"] == "final_test"]
    for part in chosen:
        base = elig if part == "final_test" else [r for r in pool if r["side"] == "dev_pool"]
        nat = {}, {}
        for r in base:
            k = (r["group"], star_bucket(r["stars"])); nat[0][k] = nat[0].get(k, 0) + 1
        for r in chosen[part]:
            k = (r["group"], star_bucket(r["stars"])); nat[1][k] = nat[1].get(k, 0) + 1
        for r in chosen[part]:
            k = (r["group"], star_bucket(r["stars"]))
            r["weight"] = round((nat[0][k] / len(base)) / (nat[1][k] / len(chosen[part])), 4)
    cols = ["id", "product", "category_group", "platform", "language_hint", "review_text", "sentiment", "confidence", "rationale"]
    ids = {}
    with open(OUT / "PRIVATE_id_map.csv", "w", newline="", encoding="utf-8") as pm:
        w = csv.writer(pm)
        w.writerow(["sheet_id", "split", "review_key", "product_link", "stars", "category_group", "platform", "sampling_weight"])
        for part, prefix in (("final_test", "T"), ("dev_pool", "D")):
            rows = chosen[part]
            for i, r in enumerate(sorted(rows, key=lambda r: r["key"]), 1):
                r["sid"] = f"{prefix}{i:03d}"
                w.writerow([r["sid"], part, r["key"], r["link"], r["stars"], r["group"], r["platform"], r["weight"]])

    def write(name, rows, seed):
        rr = list(rows)
        random.Random(seed).shuffle(rr)
        with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rr:
                w.writerow([r["sid"], " ".join(r["product"].split())[:140], r["group"], r["platform"], metrics_x.lang_of(r["text"]), r["text"].replace("\r", " ").replace("\n", " "), "", "", ""])
    write("final_test_sheet_A.csv", chosen["final_test"], 1)
    write("final_test_sheet_B.csv", chosen["final_test"], 2)
    write("dev_pool_sheet.csv", chosen["dev_pool"], 3)
    digest = hashlib.sha256("\n".join(sorted(r["key"] + "|" + hashlib.sha256(r["text"].encode()).hexdigest() for r in chosen["final_test"])).encode()).hexdigest()
    frozen = {"frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "rule": "FROZEN before any model selection. Scored once, with the final chosen model, after two independent human annotators have labelled it. Never used to tune, select or threshold.",
              "source_database_sha256": xdata.sha256(db), "final_test_ids_and_texts_sha256": digest, "sheet_sha256": {n: xdata.sha256(OUT / n) for n in ("final_test_sheet_A.csv", "final_test_sheet_B.csv", "dev_pool_sheet.csv", "PRIVATE_id_map.csv")},
              "plan": plan, "products_excluded_because_labelled_elsewhere": len(excluded_products), "group_quota": GROUP_QUOTA, "star_quota": STAR_QUOTA, "max_reviews_per_product": PER_PRODUCT,
              "stars_shown_to_annotators": False, "human_labels_in_files": 0}
    json.dump(frozen, open(OUT / "frozen_final_test.json", "w"), indent=1)
    print(json.dumps(plan, indent=1))


def PER_PER_PRODUCT_LIMIT(_side):
    return PER_PRODUCT


if __name__ == "__main__":
    main(sys.argv[1])
