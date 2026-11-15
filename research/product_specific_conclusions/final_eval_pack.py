"""The final independent evaluation pack: blind sheets for two human annotators, and the scoring (which needs real annotations).

    python research/product_specific_conclusions/final_eval_pack.py make
    python research/product_specific_conclusions/final_eval_pack.py score DIR_WITH_FILLED_SHEETS

NOTHING IN THIS PACK IS FILLED IN BY THE SYSTEM OR BY THE DEVELOPER. `make` writes empty sheets. `score` refuses to run unless two
annotators have completed enough rows, and it computes numbers only from what they wrote.

WHAT IS SAMPLED. Real products only, never constructed ones:
  * real non-electronics products from the project's own scans, taken from the HELD-OUT half and NOT among the 21 products that were read
    while the rules were written (analysed by the app's own pipeline: analyse_real_nongadget.py --skip ... --out analysed_nongadget_2);
  * saved electronics, stratified by the decision the system shows, with every kind of hazard picture present (safety warnings,
    authenticity complaints, defect reports) and with Filipino and Taglish reviews.
The electronics were used while the extraction rules were developed (the first tables came from reading that pool), so they are
NOT untouched; the non-electronics here are the closest the project has to unseen data. `key_private.csv` records which is which.

THREE SHEETS PER ANNOTATOR, DONE IN THIS ORDER (so the system's answer cannot influence the independent judgement):
  1. card_sheet:   read the reviews, then judge the overall assessment yourself. No system output is on this sheet.
  2. claims_sheet: judge each (aspect, direction, quotation) claim. No system output other than the claim itself.
  3. words_sheet:  rate two anonymous texts (old and new wording, random order) on seven dimensions. The system's assessment label is
                   shown here, so do this LAST. It is identical under both texts, so it does not reveal which text is new.
The key (`key_private.csv`) says which text was old, the system's card, the sampling stratum and the language share. Keep it from annotators.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import math
import random
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
PACK = HERE / "human_eval_pack"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))

CARDS = ("Well reviewed", "Mixed reviews", "Some concerns", "Not recommended", "Too few reviews")
DECISION_TO_CARD = {"recommended": "Well reviewed", "mixed": "Mixed reviews", "caution": "Some concerns", "not_recommended": "Not recommended", "not_enough": "Too few reviews"}
CRITERIA = ("factual", "faithful", "relevant", "sentiment", "safety", "clear", "recommendation")
CLAIM_LABELS = ("correct", "wrong_aspect", "wrong_direction", "not_about_the_product", "unclear")
CARD_COLS = ["product_id", "product", "assessment", "serious_safety_concern", "counterfeit_concern", "main_reason", "confidence"]
CLAIM_COLS = ["claim_id", "product_id", "aspect", "polarity", "review_no", "quotation", "label", "note"]
WORDS_COLS = ["product_id", "product", "assessment_shown", "text_1", "text_2"] + [f"{c}_{n}" for n in (1, 2) for c in CRITERIA] + ["unsupported_1", "unsupported_2", "safety_error_1", "safety_error_2", "preferred", "note"]
MIN_PRODUCTS = 30
MIN_CLAIMS = 50
TARGET = {"recommended": 8, "mixed": 6, "caution": 8, "not_recommended": 8, "not_enough": 4}


def collapse(text) -> str:
    return " ".join(str(text).split())


# Personal contact details that a reviewer or seller typed into a review. The pack is shared with annotators, so they are removed from
# the review text AND from the quotations (so the quotations still match). Found by the secret and personal-data scan before the commit
# (a Philippine mobile number in one review). Long digit runs are removed too (order and phone numbers); the hashes and ids in the repo
# are not in this text.
_REDACTIONS = (
    (re.compile(r"(?<!\d)(?:\+?63|0)\s?9\d{2}[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"), "[number removed]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email removed]"),
    (re.compile(r"https?://\S+|www\.\S+"), "[link removed]"),
    (re.compile(r"(?<![\w])@[A-Za-z0-9_.]{4,}"), "[handle removed]"),
    (re.compile(r"(?<!\d)\d{9,}(?!\d)"), "[number removed]"),
)


def redact(text: str) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def load_pools():
    import dashboard_utils as du

    saved = [item["product"] for item in json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8"))]
    unread_path = HERE / "cache" / "analysed_nongadget_2.json.gz"
    read_path = HERE / "cache" / "analysed_nongadget.json.gz"
    unread = json.load(gzip.open(unread_path, "rt", encoding="utf-8")) if unread_path.is_file() else []
    read_links = {p["link"] for p in json.load(gzip.open(read_path, "rt", encoding="utf-8"))} if read_path.is_file() else set()
    unread = [p for p in unread if p["link"] not in read_links]
    return du, saved, unread


def make() -> None:
    import aspects
    from before_after import load_old

    du, saved, unread = load_pools()
    old = load_old("deployment")
    rng = random.Random(20261115)
    candidates = []
    for pool, products in (("real non-electronics, unread", unread), ("saved electronics", saved)):
        for product in products:
            view = du.badge_view(product, aspects=True)
            c = view["conclusion"]
            if not c or "evidence" not in c:
                continue
            reviews = [r for r in product["comments"] if isinstance(r.get("content"), str) and r["content"].strip()]
            langs = [aspects.language_of(r["content"]) for r in reviews]
            share = sum(1 for lang in langs if lang != "en") / max(1, len(langs))
            hazards = {b["category"]: b["mentions"] for b in view["badges"]}
            candidates.append({"pool": pool, "product": product, "view": view, "c": c, "reviews": reviews, "fil_share": share, "hazards": hazards, "before": old.badge_view(product)["conclusion"]})
    # stratified pick: every real non-electronics product (they are few and are the unseen data), then fill the decision strata with electronics,
    # preferring hazard-bearing and Filipino-heavy products so the hard cases are in, not only the easy ones.
    chosen = [c for c in candidates if c["pool"].startswith("real")]
    have = collections.Counter(c["c"]["decision"] for c in chosen)
    electronics = [c for c in candidates if c["pool"] == "saved electronics"]
    rng.shuffle(electronics)
    electronics.sort(key=lambda c: -(bool(c["hazards"].get("safety")) + bool(c["hazards"].get("counterfeit")) + bool(c["hazards"].get("defect")) + (c["fil_share"] > 0.25)))
    for decision, want in TARGET.items():
        for c in [e for e in electronics if e["c"]["decision"] == decision]:
            if have[decision] >= want:
                break
            chosen.append(c)
            have[decision] += 1
    rng.shuffle(chosen)
    rows = []
    for i, c in enumerate(chosen, 1):
        rows.append({"pid": f"F{i:03d}", **c})
    PACK.mkdir(exist_ok=True)

    with open(PACK / "reviews.csv", "w", encoding="utf-8-sig", newline="") as fh:  # what annotators read: stars and text only, no reviewer, no system output
        writer = csv.writer(fh)
        writer.writerow(["product_id", "review_no", "stars", "review_text"])
        for r in rows:
            for n, review in enumerate(r["reviews"], 1):
                writer.writerow([r["pid"], n, review.get("rating", ""), redact(collapse(review["content"]))])
    index = {r["pid"]: {str(rv.get("comment_id") or f"review-{k}"): n for n, (k, rv) in enumerate([(k, rv) for k, rv in enumerate(r["product"]["comments"]) if isinstance(rv.get("content"), str) and rv["content"].strip()], 1)} for r in rows}

    claims = []
    for r in rows:
        for item in r["c"]["evidence"]["why"]:
            if item["kind"] != "product" or not item["quotes"]:
                continue
            q = item["quotes"][0]
            claims.append({"product_id": r["pid"], "aspect": item["text"].split(":")[0], "polarity": item["polarity"], "review_no": index[r["pid"]].get(q["review_id"], ""), "quotation": redact(q["text"]), "pool": r["pool"]})
    rng.shuffle(claims)
    real_claims = [c for c in claims if c["pool"].startswith("real")][:40]
    electronic_claims = [c for c in claims if c["pool"] == "saved electronics"][:40]
    sample = real_claims + electronic_claims
    rng.shuffle(sample)
    for n, claim in enumerate(sample, 1):
        claim["claim_id"] = f"C{n:03d}"

    def write(path, cols, items):
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(items)

    blank = {c: "" for c in CARD_COLS[2:]}
    for label, seed in (("A", 1), ("B", 2)):
        order = list(rows)
        random.Random(seed).shuffle(order)
        write(PACK / f"card_sheet_{label}.csv", CARD_COLS, [{"product_id": r["pid"], "product": r["product"]["name"][:100], **blank} for r in order])
        corder = list(sample)
        random.Random(seed + 10).shuffle(corder)
        write(PACK / f"claims_sheet_{label}.csv", CLAIM_COLS, [{**{k: c[k] for k in ("claim_id", "product_id", "aspect", "polarity", "review_no", "quotation")}, "label": "", "note": ""} for c in corder])
    key, words = [], []
    for r in rows:
        texts = [("old", f"{r['before']['lead']} {r['before']['summary']}"), ("new", f"{r['c']['lead']} {r['c']['summary']}")]
        rng.shuffle(texts)
        words.append({"product_id": r["pid"], "product": r["product"]["name"][:100], "assessment_shown": r["c"]["assessment"], "text_1": texts[0][1], "text_2": texts[1][1], **{c: "" for c in WORDS_COLS[5:]}})
        key.append({"product_id": r["pid"], "pool": r["pool"], "decision": r["c"]["decision"], "system_card": DECISION_TO_CARD[r["c"]["decision"]], "text_1": texts[0][0], "text_2": texts[1][0],
                    "state": r["view"]["state"], "reviews": len(r["reviews"]), "filipino_or_taglish_share": round(r["fil_share"], 2), "safety_reports": r["hazards"].get("safety", 0), "authenticity_reports": r["hazards"].get("counterfeit", 0), "defect_reports": r["hazards"].get("defect", 0), "evidence_status": r["c"]["evidence_status"]})
    for label, seed in (("A", 3), ("B", 4)):
        order = list(words)
        random.Random(seed).shuffle(order)
        write(PACK / f"words_sheet_{label}.csv", WORDS_COLS, order)
    write(PACK / "key_private.csv", list(key[0]), key)
    (PACK / "INSTRUCTIONS.md").write_text(instructions(), encoding="utf-8")
    comp = collections.Counter(k["system_card"] for k in key)
    print(f"{len(rows)} products ({sum(1 for k in key if k['pool'].startswith('real'))} real non-electronics unread, {sum(1 for k in key if k['pool'] == 'saved electronics')} electronics); cards {dict(comp)}")
    print(f"safety reports in {sum(1 for k in key if k['safety_reports'])}, authenticity reports in {sum(1 for k in key if k['authenticity_reports'])}, >=25% Filipino/Taglish in {sum(1 for k in key if k['filipino_or_taglish_share'] >= 0.25)}; {len(sample)} claims")


def instructions() -> str:
    return """# Instructions for annotators

You are helping to check whether an automatic summary of customer reviews is correct. **Work alone. Do not discuss your answers with the other annotator
and do not ask the developers what the system "should" say.** There are no right answers to guess: write what the reviews show. If you are unsure, say so in
`confidence` or `unclear`; that is useful information, not a failure.

Files: `reviews.csv` (every review of every product: stars and text; phone numbers, e-mail addresses, links and handles that people typed into reviews were removed and show as
"[number removed]" and so on), then three sheets, **to be done in this order**:
1. `card_sheet_?.csv`: read the reviews and give your own overall assessment. (No system output is on this sheet.)
2. `claims_sheet_?.csv`: judge each claim. (Only the claim and its quotation are shown.)
3. `words_sheet_?.csv`: rate two anonymous texts. (Do this last: it shows the system's assessment label.)
Use the sheet letter you were given (A or B). Do not open `key_private.csv`.

## 1. Card sheet: your own overall assessment

Choose one for `assessment`, from the reviews alone:

| Assessment | Choose it when |
|---|---|
| Well reviewed | reviews are overwhelmingly positive about the product; problems are isolated and minor; nothing a buyer needs warning about |
| Mixed reviews | a real share of positive and of negative reviews; no single serious recurring problem dominates |
| Some concerns | mostly positive or mixed, but a specific problem recurs across several reviews (a defect, doubts that it is genuine, a credible hazard report) that a buyer should weigh |
| Not recommended | mostly negative, or credible repeated reports of a hazard or of a fake product |
| Too few reviews | too few, too repetitive, too unclear, or about the delivery only: not enough to form a view of the product |

`serious_safety_concern`: yes if reviewers credibly report a risk of injury, fire, shock, a skin reaction or sickness; else no. `counterfeit_concern`: yes if several
reviewers say it is fake or not the original; else no. `main_reason`: a few words. `confidence`: high, medium or low.

## 2. Claims sheet: is the claim right?

Each row is "this review says something about <aspect> (<positive or negative>)", with the words quoted. Read the quotation (and the review, `review_no`
in `reviews.csv`, if you need the context) and write one `label`:

| label | meaning | example (invented here for illustration only) |
|---|---|---|
| correct | the quotation says this about the product, in this direction | aspect "softness", positive, "ang lambot ng buhok ko" |
| wrong_aspect | it is about something else | aspect "durability", "long-lasting fragrance" |
| wrong_direction | it says the opposite | aspect "dryness", negative, "hindi nakakadry" |
| not_about_the_product | it is about the shop, the courier, the packaging, or the buyer | aspect "ease of use", "their website was user-friendly" |
| unclear | you cannot tell | |

## 3. Words sheet: rate two texts

Read the reviews again. Text 1 and text 2 are two summaries of the same product, in random order. Rate **each** on seven dimensions, 1 (worst) to 5 (best):

| Dimension | 1 means | 5 means |
|---|---|---|
| factual | a number or plain fact is wrong (how many reviews, what share was positive) | all check out |
| faithful | something is invented or not in the reviews | everything is supported |
| relevant | generic, could be about any product | specific to what reviewers said about this product |
| sentiment | the mood is misdescribed (for example "mostly negative" for a mostly neutral product) | accurate |
| safety | a safety or fake-product report is hidden or overstated, or presented as verified | handled as unverified customer reports |
| clear | confusing | easy for an ordinary shopper on a phone |
| recommendation | the assessment shown is clearly wrong for these reviews | right |

Also: `unsupported_?` yes if the text says anything the reviews do not support; `safety_error_?` yes if it hides, invents, overstates or claims to have verified a safety or authenticity matter;
`preferred` 1, 2 or same.

### What a correct, a partly supported and an unsupported statement look like (invented illustration)
Reviews: of 100, 14 say the shampoo made their hair soft, 3 say it dried their hair, 40 only talk about delivery.
- **Supported**: "Several reviewers said it left their hair soft; a few mentioned dryness." (14 and 3 are real counts.)
- **Partly supported**: "Customers love it for softer, healthier hair." ("love" and "healthier" go beyond "soft"; "customers" suggests all.)
- **Unsupported**: "It promotes hair growth." (no review says so.)
"""


def read_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def kappa(a: list, b: list) -> float:
    """Cohen's kappa for two raters on nominal labels."""
    n = len(a)
    if n == 0:
        return float("nan")
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def weighted_kappa(a: list[int], b: list[int], k: int = 5) -> float:
    n = len(a)
    obs = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[x - 1][y - 1] += 1
    rows, cols = [sum(r) for r in obs], [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = lambda i, j: ((i - j) / (k - 1)) ** 2
    o = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k)) / n
    e = sum(w(i, j) * rows[i] * cols[j] for i in range(k) for j in range(k)) / (n * n)
    return 1.0 if e == 0 else 1 - o / e


def wilson(successes: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(centre - half, 3), round(centre + half, 3)]


def bootstrap_mean_ci(values: list[float], seed: int = 5) -> list[float]:
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(2000))
    return [round(means[50], 2), round(means[1949], 2)]


def score(folder: Path) -> dict:
    key = {r["product_id"]: r for r in read_rows(PACK / "key_private.csv")}
    out: dict = {"note": "computed only from the annotators' sheets; developer judgements are not used anywhere"}

    def both(prefix: str, id_col: str, complete) -> tuple[dict, dict, list[str]]:
        a = {r[id_col]: r for r in read_rows(folder / f"{prefix}_A.csv") if complete(r)}
        b = {r[id_col]: r for r in read_rows(folder / f"{prefix}_B.csv") if complete(r)}
        return a, b, sorted(set(a) & set(b))

    # 1. the card
    card_ok = lambda r: r["assessment"].strip() in CARDS
    ca, cb, ids = both("card_sheet", "product_id", card_ok)
    if len(ids) < MIN_PRODUCTS:
        raise SystemExit(f"Card sheets: only {len(ids)} products judged by both annotators; at least {MIN_PRODUCTS} are needed. Nothing is scored.")
    la, lb = [ca[i]["assessment"].strip() for i in ids], [cb[i]["assessment"].strip() for i in ids]
    sysc = [key[i]["system_card"] for i in ids]
    agree = lambda x, y: sum(p == q for p, q in zip(x, y))
    dangerous = sum(1 for i in ids if key[i]["system_card"] == "Well reviewed" and ca[i]["serious_safety_concern"].strip().lower() == "yes" and cb[i]["serious_safety_concern"].strip().lower() == "yes")
    out["card"] = {
        "products": len(ids),
        "annotators_exact_agreement": [agree(la, lb), len(ids), wilson(agree(la, lb), len(ids))],
        "annotators_cohens_kappa": round(kappa(la, lb), 2),
        "system_vs_annotator_A_exact": [agree(sysc, la), len(ids), wilson(agree(sysc, la), len(ids))],
        "system_vs_annotator_B_exact": [agree(sysc, lb), len(ids), wilson(agree(sysc, lb), len(ids))],
        "system_agrees_where_both_annotators_agree": [sum(1 for s, x, y in zip(sysc, la, lb) if x == y and s == x), sum(1 for x, y in zip(la, lb) if x == y)],
        "system_says_well_reviewed_while_both_flag_a_serious_safety_concern": dangerous,
        "system_card_counts": dict(collections.Counter(sysc)),
    }

    # 2. the claims
    claim_ok = lambda r: r["label"].strip() in CLAIM_LABELS
    ka, kb, cids = both("claims_sheet", "claim_id", claim_ok)
    if len(cids) < MIN_CLAIMS:
        raise SystemExit(f"Claims sheets: only {len(cids)} claims judged by both annotators; at least {MIN_CLAIMS} are needed. Nothing is scored.")
    ya, yb = [ka[c]["label"].strip() for c in cids], [kb[c]["label"].strip() for c in cids]
    right_a, right_b = sum(x == "correct" for x in ya), sum(y == "correct" for y in yb)
    strict = sum(1 for x, y in zip(ya, yb) if x == y == "correct")
    out["claims"] = {
        "claims": len(cids),
        "factual_claim_precision_annotator_A": [right_a, len(cids), wilson(right_a, len(cids))],
        "factual_claim_precision_annotator_B": [right_b, len(cids), wilson(right_b, len(cids))],
        "strict_precision_both_say_correct": [strict, len(cids), wilson(strict, len(cids))],
        "cohens_kappa_on_the_five_labels": round(kappa(ya, yb), 2),
        "label_counts_A": dict(collections.Counter(ya)),
        "label_counts_B": dict(collections.Counter(yb)),
    }

    # 3. the words
    def words_complete(r):
        try:
            return all(1 <= int(r[f"{c}_{n}"]) <= 5 for c in CRITERIA for n in (1, 2)) and all(r[f"{x}_{n}"].strip().lower() in ("yes", "no") for x in ("unsupported", "safety_error") for n in (1, 2))
        except (ValueError, KeyError):
            return False

    wa, wb, wids = both("words_sheet", "product_id", words_complete)
    if len(wids) < MIN_PRODUCTS:
        raise SystemExit(f"Words sheets: only {len(wids)} products completely rated by both annotators; at least {MIN_PRODUCTS} are needed. Nothing is scored.")

    def version(sheet, pid, criterion):
        k = key[pid]
        return {k["text_1"]: int(sheet[pid][f"{criterion}_1"]), k["text_2"]: int(sheet[pid][f"{criterion}_2"])}

    words: dict = {"products": len(wids), "criteria": {}}
    for crit in CRITERIA:
        per = {"old": [], "new": []}
        diffs = []
        for pid in wids:
            sa, sb = version(wa, pid, crit), version(wb, pid, crit)
            for v in ("old", "new"):
                per[v].append((sa[v] + sb[v]) / 2)
            diffs.append((sa["new"] + sb["new"]) / 2 - (sa["old"] + sb["old"]) / 2)
        xa = [version(wa, pid, crit)[v] for pid in wids for v in ("old", "new")]
        xb = [version(wb, pid, crit)[v] for pid in wids for v in ("old", "new")]
        words["criteria"][crit] = {"old_mean": round(statistics.fmean(per["old"]), 2), "new_mean": round(statistics.fmean(per["new"]), 2), "mean_difference_new_minus_old": round(statistics.fmean(diffs), 2),
                                   "difference_95pct_bootstrap_interval": bootstrap_mean_ci(diffs), "exact_agreement": [agree(xa, xb), len(xa)], "quadratic_weighted_kappa": round(weighted_kappa(xa, xb), 2)}
    for flag in ("unsupported", "safety_error"):
        for v in ("old", "new"):
            flagged = [(wa if s == "a" else wb)[pid][f"{flag}_{1 if key[pid]['text_1'] == v else 2}"].strip().lower() == "yes" for pid in wids for s in ("a", "b")]
            words[f"{flag}_rate_{v}_text"] = [sum(flagged), len(flagged), wilson(sum(flagged), len(flagged))]
    prefs = collections.Counter()
    for pid in wids:
        for sheet in (wa, wb):
            choice = sheet[pid]["preferred"].strip().lower()
            prefs["same" if choice not in ("1", "2") else key[pid][f"text_{choice}"]] += 1
    words["preferred"] = dict(prefs)
    out["words"] = words
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("make")
    s = sub.add_parser("score")
    s.add_argument("folder", type=Path, help="a folder holding card_sheet_A/B.csv, claims_sheet_A/B.csv and words_sheet_A/B.csv, filled in by the annotators")
    args = parser.parse_args()
    if args.command == "make":
        make()
    else:
        print(json.dumps(score(args.folder), indent=1))


if __name__ == "__main__":
    main()
