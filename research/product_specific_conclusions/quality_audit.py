"""Automatic audit of the generated conclusions for the failure modes the panel cares about.

    python research/product_specific_conclusions/quality_audit.py

Runs over every available real pool: the 182 saved electronics, the 21 real non-electronics products read while the rules were written,
and the unread second set (cache/analysed_nongadget_2). It checks the TEXT against the data the text was made from:

  contradiction   headline, paragraph and assessment agree with the decision (for example "generally well received" only for `recommended`)
  majority        a count word is never stronger than its count allows; "most" needs a majority; an isolated complaint is never "recurring"
  neutral         "mostly negative" or a negative majority is never said unless the negative share is a majority
  hazard          every safety or authenticity count the hazard checker found is in the warnings, and a warning exists only for a found count
  benefit         no medical, cosmetic or performance benefit that no aspect supports (hair growth, whitening, cure, immunity, weight loss ...)
  delivery        delivery, packaging, seller or freebie comments never stand in for product praise
  authenticity    no sentence says a product IS genuine, fake or counterfeit; "described it as genuine" is a report and needs >= 2 reviews
  evidence        every line has a valid count and quotation (the full mechanical check is evidence_verification.py)

These are rules about what the text may say. They cannot tell whether the text is TRUE of the reviews: that is what the human sheets
(human_eval_pack) are for. Writes quality_audit.md and quality_audit.json.
"""
from __future__ import annotations

import collections
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

import aspects as aspects_module  # noqa: E402
import dashboard_utils as du  # noqa: E402
from aspect_profiles import EVIDENCE_POLICY  # noqa: E402

CARD = {"recommended": "Well reviewed", "mixed": "Mixed reviews", "caution": "Some concerns", "not_recommended": "Not recommended", "not_enough": "Too few reviews"}
BENEFIT = re.compile(r"\b(?:hair\s+growth|grow(?:s|th)?\s+(?:hair|back)|regrow\w*|whiten\w*|brighten\w*|anti[- ]?ag\w*|wrinkle\w*|cure[sd]?|heals?|healed|treat(?:s|ed|ment)\b|detox\w*|lose\s+weight|weight\s+loss|fat\s+burn\w*|muscle\s+(?:gain|growth|build\w*)|immun\w*|boosts?\s+(?:your\s+)?(?:energy|metabolism)|prevents?\s+\w+)\b", re.I)
DELIVERY_WORDS = re.compile(r"\b(?:delivery|shipping|packag\w*|seller|rider|freebies?)\b", re.I)
VERDICT_LEADS = {
    "recommended": re.compile(r"generally well received|favorable|Although customer feedback is generally positive", re.I),
    "mixed": re.compile(r"mixed", re.I),
    "caution": re.compile(r"favorable|praised|think twice|concern", re.I),
    "not_recommended": re.compile(r"raises concerns|drew few positive", re.I),
    "not_enough": re.compile(r"too few", re.I),
}


def pools():
    saved = [item["product"] for item in json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8"))]
    out = [("saved electronics", saved)]
    for name, file in (("real non-electronics (read while tuning)", "analysed_nongadget.json.gz"), ("real non-electronics (unread)", "analysed_nongadget_2.json.gz")):
        path = HERE / "cache" / file
        if path.is_file():
            out.append((name, json.load(gzip.open(path, "rt", encoding="utf-8"))))
    return out


def audit(name: str, products: list[dict]) -> dict:
    counts = collections.Counter()
    flagged: dict[str, list[str]] = collections.defaultdict(list)

    def flag(kind: str, product: dict, detail: str) -> None:
        counts[kind] += 1
        if len(flagged[kind]) < 8:
            flagged[kind].append(f"{product['name'][:55]} | {detail}")

    for product in products:
        view = du.badge_view(product, aspects=True)
        c = view["conclusion"]
        if not c or "evidence" not in c:
            continue
        counts["conclusions"] += 1
        decision, lead, text = c["decision"], c["lead"], f"{c['lead']} {c['summary']}"
        shares = du._sentiment_shares(product["sentiment_summary"]) or {}
        mentions = {b["category"]: b["mentions"] for b in view["badges"]}
        why = c["evidence"]["why"]
        product_lines = {w["text"].split(":")[0].lower(): w for w in why if w["kind"] == "product"}

        # contradiction
        if c["assessment"] != CARD[decision]:
            flag("contradiction", product, f"assessment {c['assessment']!r} for decision {decision}")
        if not VERDICT_LEADS[decision].search(lead):
            flag("contradiction", product, f"headline does not match decision {decision}: {lead[:90]}")
        if decision != "recommended" and re.search(r"generally well received|Although customer feedback is generally positive", lead):
            flag("contradiction", product, f"'well received' with decision {decision}")
        if decision in ("caution", "not_recommended") and not (c.get("warnings") or re.search(r"report|concern|dispute|disagree|problem|issue", text, re.I)):
            flag("contradiction", product, f"{decision} text names no concern")
        if decision == "recommended" and re.search(r"\bthink twice|raises concerns|advise against\b", text, re.I):
            flag("contradiction", product, "recommended text warns against it")

        # majority / strength
        if re.search(r"\bMost reviewers\b|\bmost reviewers (?:praised|reported|mentioned)\b", text):
            flag("majority", product, "'most reviewers' about aspect counts")
        # every count word must be exactly the word the evidence policy gives for the count of the aspect it describes
        by_side = {(w["polarity"], w["text"].split(":")[0].lower().replace("problems with ", "").strip()): w for w in why if w["kind"] == "product"}
        considered = c["evidence"]["reviews_considered"]
        for sentence in re.split(r"(?<=\.)\s+", c["summary"]):
            polarity = None
            for m in re.finditer(r"\b(One reviewer|Some reviewers|Several reviewers|Many reviewers|one|some|several|many)\s+(praised|reported|mentioned)\s+([^,.;]+)", sentence):
                polarity = polarity or ("positive" if m.group(2) == "praised" else "negative")
                word = m.group(1).split()[0].lower()
                for part in re.split(r" and ", m.group(3)):
                    key = part.replace("problems with", "").strip().lower()
                    line = by_side.get((polarity, key))
                    if line is None:
                        continue
                    expected = aspects_module.tier_word(line["reviews"], considered)
                    if word != expected:
                        flag("majority", product, f"'{word}' for {key!r} ({polarity}) but {line['reviews']} reviews of {considered} give '{expected}'")
        if re.search(r"\brecurring|repeatedly\b", text, re.I):
            flag("majority", product, "'recurring' is not a phrase this writer uses; check")

        # neutral misread
        negative, neutral = shares.get("negative", 0), shares.get("uncertain", 0)
        if re.search(r"mostly negative|negative majority|most reviewers were negative", text) and negative <= 0.5:
            flag("neutral", product, f"negative {negative:.0%}")
        if neutral >= 0.5 and re.search(r"predominantly positive|mostly positive", text):
            flag("neutral", product, f"neutral {neutral:.0%}")

        # hazards
        warnings = c.get("warnings", [])
        for key, pattern in (("safety", "possible safety problem"), ("counterfeit", "question")):
            has = any(re.search(pattern, w) for w in warnings)
            if mentions.get(key) and not has:
                flag("hazard", product, f"{key} reports {mentions[key]} but no warning")
            if has and not mentions.get(key):
                flag("hazard", product, f"a {key} warning without a count")
        if any("possible safety problem" in w for w in warnings) and not any("not been independently verified" in w for w in warnings):
            flag("hazard", product, "safety warning not marked unverified")

        # benefit claims no aspect supports
        for m in BENEFIT.finditer(text):
            flag("benefit", product, f"'{m.group(0)}' in the conclusion")

        # delivery standing in for product praise
        if decision in ("recommended",) and c["evidence_status"] == "supported" and re.search(r"praise[sd]?\s+(?:[^.]*\b)?(?:delivery|packag\w*|seller)", lead, re.I):
            flag("delivery", product, f"lead praises {lead[:90]}")
        if c["evidence_status"] == "limited" and re.search(r"generally well received", lead):
            flag("delivery", product, "limited evidence but 'well received'")

        # authenticity wording
        if re.search(r"(?<!whether the product )(?<!whether it )\b(?:is|are)\s+(?:genuine|authentic|counterfeit|fake)\b", text, re.I):
            flag("authenticity", product, "states genuineness as fact")
        m = re.search(r"(One|Some|Several|Many) reviewers described it as genuine", text)
        if m:
            line = next((w for w in why if w["aspect"] == "authenticity" and w["polarity"] == "positive"), None)
            if not line or line["reviews"] < EVIDENCE_POLICY["lead_min_reviews"] or mentions.get("counterfeit"):
                flag("authenticity", product, "'described it as genuine' without enough support or despite doubts")

        # evidence shape
        for w in why:
            if w["reviews"] < 1 or not w["quotes"]:
                flag("evidence", product, f"line without count or quotation: {w['text']}")
        words = len(text.split())
        counts["words_total"] += words
        counts["words_max"] = max(counts["words_max"], words)
        if words > EVIDENCE_POLICY["target_words"]:
            flag("evidence", product, f"{words} words")
    return {"pool": name, "products": len(products), "conclusions": counts["conclusions"], "issues": {k: counts[k] for k in ("contradiction", "majority", "neutral", "hazard", "benefit", "delivery", "authenticity", "evidence")}, "words_max": counts["words_max"], "flagged": dict(flagged)}


def main() -> None:
    results = [audit(name, products) for name, products in pools()]
    (HERE / "quality_audit.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    md = ["# Conclusion quality audit (automatic)", "", "Generated by `quality_audit.py`. **These are rules about what the text may say**, checked against the data it was made from. They cannot tell whether the text is true of the reviews; only the human sheets can.", "",
          "| Pool | Conclusions | Contradiction | Majority | Neutral | Hazard | Benefit | Delivery | Authenticity | Evidence | Longest (words) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        i = r["issues"]
        md.append(f"| {r['pool']} | {r['conclusions']} | {i['contradiction']} | {i['majority']} | {i['neutral']} | {i['hazard']} | {i['benefit']} | {i['delivery']} | {i['authenticity']} | {i['evidence']} | {r['words_max']} |")
    for r in results:
        for kind, items in r["flagged"].items():
            md += ["", f"### {r['pool']}: {kind}", ""] + [f"- {x}" for x in items]
    md.append("")
    (HERE / "quality_audit.md").write_text("\n".join(md), encoding="utf-8")
    for r in results:
        print(r["pool"], r["conclusions"], r["issues"], "longest", r["words_max"])
        for kind, items in r["flagged"].items():
            for x in items[:4]:
                print("   ", kind, "|", x)


if __name__ == "__main__":
    main()
