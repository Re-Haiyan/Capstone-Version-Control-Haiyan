"""Rebuild tests/fixtures/conclusion_cases.json: real server output for the card's browser test.

    python research/product_specific_conclusions/make_ui_fixture.py

Each case is `with_badge_view(product, aspects=True)` for a REAL saved product (electronics) or a REAL analysed non-electronics
product (cache/analysed_nongadget.json.gz, if present), with the review list emptied: only the conclusion, its warnings and its
quotations travel with the fixture. One case is a saved product renamed with a very long shampoo name and given delivery-only
reviews, to exercise the "limited evidence" card and a long name (that case is labelled in its name as constructed).
"""
from __future__ import annotations

import copy
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

import dashboard_utils as du  # noqa: E402


def main() -> None:
    saved = [item["product"] for item in json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8"))]
    by = lambda prefix: next(p for p in saved if p["name"].startswith(prefix))
    cases = {"caution": by("Essager 10W"), "recommended": by("WOMINGTE"), "not_recommended": by("2 in 1 Universal")}
    cache = HERE / "cache" / "analysed_nongadget.json.gz"
    if cache.is_file():
        real = json.load(gzip.open(cache, "rt", encoding="utf-8"))
        pick = lambda prefix: next((p for p in real if p["name"].startswith(prefix)), None)
        for key, prefix in (("real_skin_with_warnings", "Cetaphil Gentle Skin Cleanser 1L"), ("real_apparel_mixed", "Rubie Challis"), ("real_appliance_safety", "OOKAS rice cooker")):
            if pick(prefix):
                cases[key] = pick(prefix)
    limited = copy.deepcopy(by("WOMINGTE"))
    limited["name"] = "[CONSTRUCTED CASE] Silka Premium Moisturizing Shampoo with Argan Oil and Keratin for Dry and Damaged Hair 500ml Family Size Value Pack Bundle Super Long Product Name"
    limited["link"] = "https://www.lazada.com.ph/products/limited-demo.html"
    texts = ["Fast delivery", "Mabilis ang delivery, salamat rider", "Well packed", "Maayos ang packaging", "Fast shipping thank you seller", "ok", "Received po", "Thank you seller", "Maganda ang packaging"] * 3
    limited["comments"] = [{"comment_id": f"L{i}", "content": text, "rating": 5, "author": f"r{i}"} for i, text in enumerate(texts)]
    cases["limited_long_name"] = limited
    out = {}
    for key, product in cases.items():
        full = du.with_badge_view(copy.deepcopy(product), aspects=True)
        card = {k: v for k, v in full.items() if k != "comments"}
        detail = dict(full, comments=[])
        out[key] = {"link": product["link"], "detail": {"product": detail, "recommendations": []}, "card": card}
        c = full["badge_view"]["conclusion"]
        print(f"{key:26} {c['decision']:16} warnings={len(c.get('warnings', []))} words={len((c['lead'] + ' ' + c['summary']).split())}")
    (ROOT / "tests" / "fixtures" / "conclusion_cases.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
