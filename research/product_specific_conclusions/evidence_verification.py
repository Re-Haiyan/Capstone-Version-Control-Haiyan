"""Verify EVERY claim the card shows against the original reviews, on the saved electronics and on the real non-electronics sample.

    python research/product_specific_conclusions/evidence_verification.py

For each line of "Why this conclusion?" and each of its quotations it checks, mechanically:
  1. the review exists (by comment_id, or by "review-<position>" when a saved review has none);
  2. the quotation is a verbatim slice of that review (whitespace collapsed), at the stated [start, end), cut only with a final "…";
  3. the review identifiers listed for a line are unique, valid, and as many as the count says (the list is capped, the count is exact);
  4. the count of a line equals what aspects.extract finds again from the reviews (reproducible);
  5. no review is counted for both praise and complaint of the same aspect (such a review counts for neither);
  6. no two reviews counted for one aspect and side have the same normalised text (copied reviews count once);
  7. the aspect belongs to the product's profile (a clothing aspect never appears on a charger);
  8. nothing about the reviewer (author, name, id of the reviewer) is in the conclusion payload.
It does NOT check that the aspect is the right one for the sentence or that the direction is right: that is a judgement, and is
what aspect_validation_sample.csv and human_evaluation.md are for. Writes evidence_verification.json and evidence_verification.md.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

import aspect_profiles as ap  # noqa: E402
import aspects  # noqa: E402
import dashboard_utils as du  # noqa: E402


def collapse(text: str) -> str:
    return " ".join(str(text).split())


def verify(pool_name: str, products: list[dict]) -> dict:
    counts = {k: 0 for k in ("products_with_evidence", "lines", "quotations", "review_ids_listed")}
    problems: list[str] = []
    for product in products:
        view = du.badge_view(product, aspects=True)
        conclusion = view["conclusion"]
        if not conclusion or "evidence" not in conclusion:
            continue
        counts["products_with_evidence"] += 1
        comments = product["comments"]
        by_id = {f"review-{i}": c for i, c in enumerate(comments)} | {str(c["comment_id"]): c for c in comments if c.get("comment_id")}
        category, group = du.product_category_of(product), du.product_group(product)
        again = aspects.extract(comments, category, group)
        again_rows = {r["id"]: r for r in again["aspects"]}
        profile_ids = {a.id for a in ap.aspects_for(category, group)}
        per_aspect: dict[str, dict[str, set]] = {}
        name = product["name"][:50]
        for item in conclusion["evidence"]["why"]:
            counts["lines"] += 1
            tag = f"{pool_name}:{name}:{item['aspect']}:{item['polarity']}"
            if item["aspect"] not in profile_ids:
                problems.append(f"{tag}: aspect not in this product's profile")
            row = again_rows.get(item["aspect"])
            if not row or row[item["polarity"]]["reviews"] != item["reviews"]:
                problems.append(f"{tag}: count {item['reviews']} is not reproduced by extracting again")
            ids = item["review_ids"]
            counts["review_ids_listed"] += len(ids)
            expected = len(ids) if item["ids_truncated"] else item["reviews"]
            if len(ids) != len(set(ids)) or len(ids) != expected:
                problems.append(f"{tag}: review ids not unique or not as many as the count")
            if any(rid not in by_id for rid in ids):
                problems.append(f"{tag}: an id does not exist")
            texts = [re.sub(r"\W+", "", aspects.fold(by_id[rid]["content"])) for rid in ids if rid in by_id]
            if len(texts) != len(set(texts)):
                problems.append(f"{tag}: two counted reviews have the same text")
            per_aspect.setdefault(item["aspect"], {}).setdefault(item["polarity"], set()).update(ids)
            for quote in item["quotes"]:
                counts["quotations"] += 1
                review = by_id.get(quote["review_id"])
                if not review:
                    problems.append(f"{tag}: quotation review missing")
                    continue
                raw = str(review["content"])
                text = quote["text"]
                sliced = collapse(raw[quote["span"][0] : quote["span"][1]]) if quote["span"] else None
                cut = text.endswith("…") and sliced != text
                body = text[:-1].rstrip() if cut else text
                if body not in collapse(raw):
                    problems.append(f"{tag}: quotation not in the review")
                elif sliced is not None and not (sliced == text or (cut and sliced.startswith(body))):
                    problems.append(f"{tag}: quotation is not at its stated span")
                if quote["review_id"] not in ids and not item["ids_truncated"]:
                    problems.append(f"{tag}: quotation review not among the listed ids")
        for aspect_id, sides in per_aspect.items():
            if len(sides) == 2 and sides.get("positive", set()) & sides.get("negative", set()):
                problems.append(f"{pool_name}:{name}:{aspect_id}: a review counted for both praise and complaint")
        payload = json.dumps(conclusion, ensure_ascii=False)
        for key in ('"author"', '"reviewer"', '"user_name"', '"username"'):
            if key in payload:
                problems.append(f"{pool_name}:{name}: {key} in the payload")
    return {"pool": pool_name, "products": len(products), **counts, "problems": problems}


def main() -> None:
    saved = [item["product"] for item in json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8"))]
    pools = [verify("saved electronics", saved)]
    cache = HERE / "cache" / "analysed_nongadget.json.gz"
    if cache.is_file():
        pools.append(verify("real non-electronics (read while tuning)", json.load(gzip.open(cache, "rt", encoding="utf-8"))))
    unread = HERE / "cache" / "analysed_nongadget_2.json.gz"
    if unread.is_file():
        pools.append(verify("real non-electronics (unread)", json.load(gzip.open(unread, "rt", encoding="utf-8"))))
    (HERE / "evidence_verification.json").write_text(json.dumps(pools, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [
        "# Evidence verification",
        "",
        "Generated by `evidence_verification.py`. Every figure below is computed, none typed.",
        "",
        "What is checked, mechanically, for every line of \"Why this conclusion?\" and every quotation: the review exists; the quotation is a verbatim slice of it at the stated position; "
        "the review ids are unique, valid and as many as the count; the count is reproduced by reading the reviews again; no review counts for both praise and complaint of one aspect; "
        "no two counted reviews have the same text; the aspect belongs to the product's profile; no reviewer field is in the payload.",
        "",
        "**Not checked here**: whether the aspect is the right one for the sentence and whether the direction is right. That is judgement. "
        "`precision_check.md` and `aspect_validation.md` record the developer's informal judgements and `human_evaluation.md` asks for independent ones.",
        "",
        "| Pool | Products with evidence | Lines | Quotations | Review ids listed | Problems found |",
        "|---|---|---|---|---|---|",
    ]
    for p in pools:
        md.append(f"| {p['pool']} | {p['products_with_evidence']} of {p['products']} | {p['lines']} | {p['quotations']} | {p['review_ids_listed']} | {len(p['problems'])} |")
    for p in pools:
        if p["problems"]:
            md += ["", f"### Problems in {p['pool']}", ""] + [f"- {x}" for x in p["problems"][:40]]
    md.append("")
    (HERE / "evidence_verification.md").write_text("\n".join(md), encoding="utf-8")
    for p in pools:
        print(p["pool"], {k: v for k, v in p.items() if k != "problems"}, "problems:", len(p["problems"]))
        for x in p["problems"][:10]:
            print("  ", x)


if __name__ == "__main__":
    main()
