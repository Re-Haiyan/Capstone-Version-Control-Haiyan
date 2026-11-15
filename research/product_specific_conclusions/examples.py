"""Example conclusions: real saved products, and constructed review sets for product types the saved pool lacks.

    python research/product_specific_conclusions/examples.py

Writes examples.md. PART A is real: saved Lazada listings and their real reviews, old text from the code on --before-rev
(default: deployment) and new text from this code. PART B is SYNTHETIC: the saved pool holds only electronics, so shampoo,
clothing, food and similar are shown with review sets written by the developer for this document. They show what the
rules do with such reviews; they are not evidence about any real product. PART C lists where the new text is wrong or weak.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))

import category_copy  # noqa: E402
import dashboard_utils as new  # noqa: E402
from before_after import load_old  # noqa: E402


def reviews(texts, rating=5):
    stars = rating if isinstance(rating, list) else [rating]
    return [{"comment_id": f"s{i}", "content": text, "rating": stars[i % len(stars)]} for i, text in enumerate(texts)]


def summary(positive, uncertain, negative):
    total = positive + uncertain + negative
    return {"sentiment_counts": {"positive": positive, "uncertain": uncertain, "negative": negative}, "positive_ratio_lower_bound": positive / total * 0.9}


def synthetic(name, comments, state="no_warning_signs", mood=(80, 12, 8), safety=0, counterfeit=0, defect=0):
    found = [{"category": "safety", "mentions": safety}, {"category": "counterfeit", "mentions": counterfeit}, {"category": "defect", "mentions": defect}]
    product = {"name": name, "link": f"synthetic://{name}", "comments": comments}
    words = category_copy.profile(new.product_group(product))
    data = summary(*mood)
    base = new._conclusion(data, state, found, len(comments), words)
    return new._ground_conclusion(base, product, data, state, found, len(comments), words), base


def block(title, name, category, c, old=None):
    lines = [f"### {title}", "", f"*{name}* · category `{category}` · decision `{c['decision']}` · evidence `{c.get('evidence_status', 'none')}`", ""]
    if old:
        lines += ["**Before** (current wording)", "", f"> **{old['lead']}** {old['summary']}", ""]
    note = f" · {c['assessment_note']}" if c.get("assessment_note") else ""
    lines += ["**After**", "", f"> **{c['lead']}** {c['summary']}", "", f"*Overall assessment: {c['assessment']}*{note}", ""]
    why = (c.get("evidence") or {}).get("why", [])
    if why:
        lines += ["Why this conclusion? (first lines, with one quotation each)", ""]
        for item in why[:5]:
            quote = item["quotes"][0]["text"] if item["quotes"] else ""
            lines.append(f"- {item['text']} (`{item['kind']}`): “{quote}”")
        lines.append("")
    return lines


SETS = [
    (
        "A. Shampoo, favorable",
        "Silka Shampoo 500ml",
        ["Ang lambot ng buhok ko pagkatapos gamitin", "My hair feels smoother after washing", "Ang ganda ng amoy, sobrang bango", "Mabango and soft talaga", "Soft ang buhok ko, bango pa", "Ang bango niya, lambot ng buhok", "Gusto ko ang amoy, malambot buhok ko", "smooth hair after use, nice scent", "Medyo drying sa dulo pero ok naman", "Nangati anit ko ng konti", "Sobrang sulit, mura pero ok", "Fast delivery", "ok", "Maganda"],
        "no_warning_signs",
        (82, 12, 6),
        {},
    ),
    (
        "B. Wireless earbuds, favorable with a minor issue",
        "TWS Wireless Earbuds Bluetooth 5.3",
        ["Ganda ng tunog, malinaw ang sound", "Sound quality is great for the price", "Comfortable sa tenga, hindi masakit", "Matagal ang battery, tipid", "Battery life is good", "Comfortable fit and secure", "Clear ang sound, malakas ang bass", "nagdi-disconnect minsan", "Minsan nagdi-disconnect ang kaliwa", "Sulit, super bilis ng delivery", "Great sound and comfy", "ganda ng tunog niya", "maganda ang battery", "Secure ang fit"],
        "no_warning_signs",
        (80, 14, 6),
        {},
    ),
    (
        "C. Hair treatment, mixed",
        "Hair Treatment Mask 250ml",
        ["Ang lambot ng buhok ko", "Soft and smooth after use", "malambot talaga", "Smoother hair, I love it", "lambot ng buhok", "Ang drying ng buhok ko", "Nagdry buhok ko sobra", "drying siya sa akin", "Hindi effective sa buhok ko", "Hindi effective, walang epekto", "Hindi ko nagustuhan ang amoy, mabaho", "Not effective for me"],
        "no_warning_signs",
        (45, 20, 35),
        {},
    ),
    (
        "D. Power bank, not recommended",
        "20000mAh Power Bank Fast Charging",
        ["Hindi umabot ang 20000mAh, isang charge lang", "Capacity is fake, mababa ang mah", "Biglang namamatay habang nagcha-charge", "namamatay lang bigla", "Ayaw mag-charge ng phone ko", "Hindi nagcha-charge, charging issue", "Mabagal ang charging", "slow charging talaga", "Sira agad after 1 week", "Nasira agad after 2 weeks", "Umiinit ng sobra", "Overheating ang powerbank", "Okay naman ang itsura"],
        "no_warning_signs",
        (18, 12, 70),
        {},
    ),
    (
        "E. Shampoo, delivery and packaging only (limited product evidence)",
        "Pantene Shampoo 750ml",
        ["Fast delivery", "Mabilis ang delivery", "Well packed", "Maayos ang packaging", "Fast shipping, thank you rider", "Salamat seller", "Maganda ang packaging", "ok", "Received po", "Mabilis dumating, maayos ang balot", "Secure packaging", "on time delivery"],
        "no_warning_signs",
        (70, 25, 5),
        {},
    ),
    (
        "F. T-shirt, size and fabric complaints",
        "Cotton T-shirt Oversized Unisex",
        ["Masyadong maliit ang size", "Too small, runs small", "Manipis ang tela", "see-through ang tela", "Hindi kasya sa akin", "sumikip agad", "Maayos ang tahi", "Ang ganda ng kulay", "Presko suotin, comfortable", "Sulit sa presyo"],
        "no_warning_signs",
        (35, 15, 50),
        {},
    ),
    (
        "G. Snack, freshness complaints",
        "Crispy Chips Snack Pack 10pcs",
        ["Panis na pagdating", "Stale na ang chips", "expired na", "Malapit na mag-expire", "may langgam sa loob", "Lipas na", "Masarap naman ang lasa", "Sarap ng lasa", "Marami ang laman, sulit"],
        "no_warning_signs",
        (30, 15, 55),
        {},
    ),
    (
        "H. Favorable sentiment, serious hazard reports",
        "20000mAh Power Bank",
        ["Fast charging, ang bilis", "Sulit, matibay", "Ganda ng design", "Maganda ang quality"] * 4 + ["Nag-overheat at umusok", "Umusok yung powerbank"],
        "safety_warning",
        (92, 4, 4),
        {"safety": 3},
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-rev", default="deployment")
    old = load_old(parser.parse_args().before_rev)
    products = [x["product"] for x in json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8"))]
    out = ["# Example conclusions", "", "Generated by `examples.py`. Nothing here is hand-edited.", "", "## Part A. Real saved products", ""]
    seen = set()
    for decision, status in [("recommended", "supported"), ("caution", "supported"), ("not_recommended", "supported"), ("mixed", "supported"), ("recommended", "limited"), ("not_enough", "supported")]:
        for product in products:
            c = new.badge_view(product, aspects=True)["conclusion"]
            if c and c["decision"] == decision and c.get("evidence_status") == status and product["link"] not in seen:
                seen.add(product["link"])
                out += block(f"{decision} / {status}", product["name"][:95], new.product_category_of(product), c, old.badge_view(product)["conclusion"])
                break
    out += ["## Part B. Constructed review sets (SYNTHETIC: written for this document, not real products)", ""]
    for title, name, texts, state, mood, kw in SETS:
        stars = [5, 4, 5, 5, 4] if mood[0] > 50 else [1, 2, 1, 3]
        c, base = synthetic(name, reviews(texts * (2 if len(texts) < 16 else 1), rating=stars), state, mood, **kw)
        out += block(title, name, new.product_category_of({"name": name}), c, base)
    out += ["## Part C. Where the new conclusion is wrong or weak", "", "Real cases from the saved pool, found by reading outputs; see `precision_check.md` for the claim-level error classes.", ""]
    threshold_cases = []
    for product in products:
        view = new.badge_view(product, aspects=True)
        c = view["conclusion"]
        shares = new._sentiment_shares(product["sentiment_summary"]) or {}
        if c and c["decision"] == "not_recommended" and shares.get("negative", 0) < 0.3 and view["state"] == "no_warning_signs":
            threshold_cases.append((product, c, shares))
    out.append(
        f"1. **A decision rule this feature does not change.** {len(threshold_cases)} saved product(s) are `not_recommended` with no warning signs and fewer than 30% negative reviews. "
        "The decision rule uses the POSITIVE share only (below 50% is `not_recommended`), so a neutral-heavy product lands there. The new text describes the distribution accurately instead of "
        "calling it negative, but the decision value is unchanged on purpose; the thresholds are the team's to review."
    )
    for product, c, shares in threshold_cases[:2]:
        out += ["", f"   *{product['name'][:80]}*: positive {round(shares['positive'] * 100)}%, neutral or unclear {round(shares['uncertain'] * 100)}%, negative {round(shares['negative'] * 100)}%.", f"   > **{c['lead']}** {c['summary']}"]
    out += [
        "",
        "2. **A generic aspect says little.** For electronics the reason is often \"performance in use\" (it works or it does not). It is true to the reviews but it is not a product feature; a richer profile for chargers, mice and smartwatches would help.",
        "3. **Recall is traded for precision.** Menu-tag blocks and terse capitalised lists (\"Good quality, Fast delivery.\") are skipped, so some genuine short reviews do not count, and a few products move to `limited` because of it.",
        "4. **Seven of ten profiles have not met real reviews.** Hair, skin, apparel, footwear, food, appliance and motorcycle profiles are exercised only by the constructed sets above and the unit tests.",
        "",
    ]
    (HERE / "examples.md").write_text("\n".join(out), encoding="utf-8")
    print("wrote", HERE / "examples.md", len(out), "lines")


if __name__ == "__main__":
    main()
