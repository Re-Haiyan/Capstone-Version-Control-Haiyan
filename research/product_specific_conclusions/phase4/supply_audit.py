"""Read-only supply audit: how many locally held reviews would survive the Phase 4 historical-exclusion gates IF the owner confirmed their use rights.

    python research/product_specific_conclusions/phase4/supply_audit.py --db /path/to/defaketive.db [--out summary.json]

It does NOT create D3/V3/F2, does NOT write review text anywhere, does NOT set or imply `rights_confirmed`, and cannot establish rights: a local database copy of marketplace reviews is
not evidence of permission to use it for research. It reuses intake.py's exclusion logic (historical product titles / link hashes / review texts, near-duplicates within the supply) and reports
aggregate counts only (no reviews, no listing URLs, no titles). Output is for deciding whether an authorised export is worth requesting, not for model development.
"""
import argparse, collections, json, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    index, old_titles, old_hashes = intake.historical_index()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    seen = intake.OverlapIndex()
    c = collections.Counter(); prod = collections.Counter(); split_reviews = collections.Counter(); split_products = collections.defaultdict(set)
    groups = collections.Counter(); cats = collections.Counter()
    for raw, in con.execute("select raw_json from products where raw_json is not null"):
        try:
            p = json.loads(raw)
        except ValueError:
            c["product_unparsable"] += 1
            continue
        c["products_in_database"] += 1
        link = str(p.get("link") or p.get("url") or "")
        title = str(p.get("title") or p.get("name") or "")
        if not link or not title:
            c["product_missing_link_or_title"] += 1
            continue
        if intake.historic_link_hash(link) in old_hashes:
            prod["excluded_phase3_link_hash"] += 1
            continue
        if intake.title_overlaps(title, old_titles):
            prod["excluded_historical_title"] += 1
            continue
        comments = [x for x in (p.get("comments") or []) if isinstance(x, dict) and str(x.get("content") or "").strip()]
        prod["products_not_historical"] += 1
        kept = 0
        host = "lazada" if "lazada" in link else "shopee" if "shopee" in link else "other"
        key = intake.product_hash(host, link)
        for x in comments:
            t = str(x["content"])
            c["reviews_in_not_historical_products"] += 1
            if index.is_duplicate(t):
                c["review_duplicates_historical_text"] += 1
                continue
            if seen.is_duplicate(t):
                c["review_duplicate_within_supply"] += 1
                continue
            seen.add(t)
            kept += 1
            sp = intake.split_for(host, key)
            split_reviews[sp] += 1; split_products[sp].add(key)
        if kept:
            prod["products_with_surviving_reviews"] += 1
            groups[str(p.get("category_group") or p.get("group") or "unknown")] += 1
    out = {"purpose": "supply estimate only; rights NOT established; no dataset created",
           "split_estimate_not_intake_assignment": True,
           "split_estimate_caveat": "URL proxy hashed twice; actual intake requires a verified canonical listing_id and may yield different D3/V3/F2 counts",
           "privacy_and_intake_eligibility_not_verified": True,
           "counts": dict(c), "products": dict(prod),
           "surviving_reviews_by_split_if_rights_were_confirmed": dict(split_reviews), "surviving_products_by_split": {k: len(v) for k, v in split_products.items()},
           "targets": intake.TARGET, "product_groups_with_surviving_reviews": dict(groups)}
    print(json.dumps(out, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
