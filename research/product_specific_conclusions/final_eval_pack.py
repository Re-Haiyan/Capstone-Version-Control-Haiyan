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
FEATURE_COLS = ["item_id", "product_id", "review_no", "profile", "stars", "review_text", "features", "note"]
MIN_FEATURE_ITEMS = 40  # reviews judged by both annotators before recall and F1 are computed
N_FEATURE_REVIEWS = 150
ANNOTATOR_TYPES = ("human", "ai_assisted")  # ai_assisted covers any AI: the provenance record names which (ChatGPT, Claude ...) and who actually did the work
PROVENANCE_KEYS = ("label", "type", "annotator", "model_version", "interface", "dates", "prompt_file", "human_review_of_labels")
TARGET_F1 = 0.80
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
    make_features(rows, random.Random(20261116), write, aspects, du)
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


def make_features(rows, rng, write, aspects, du) -> None:
    """Review-level sheet for recall: the annotator lists every product feature a review states, from a fixed vocabulary, WITHOUT seeing the system.

    The system's own reading of the same reviews goes to features_key_private.csv, which annotators never receive.
    """
    from aspect_profiles import aspects_for, profile_key

    pool = []
    for r in rows:
        category, group = du.product_category_of(r["product"]), du.product_group(r["product"])
        profile = profile_key(category, group)
        for n, review in enumerate(r["reviews"], 1):
            if len(str(review["content"]).strip()) >= 20:
                pool.append((r, n, review, category, group, profile))
    rng.shuffle(pool)
    sample = pool[:N_FEATURE_REVIEWS]
    items, key, vocabulary = [], [], {}
    for k, (r, n, review, category, group, profile) in enumerate(sample, 1):
        for a in aspects_for(category, group):
            vocabulary[(profile, a.id)] = (a.label, a.kind)
        system = sorted({f"{row['id']}:{pol}" for row, pol, _side in aspects.iter_claims(aspects.extract([review], category, group))})
        item = {"item_id": f"R{k:03d}", "product_id": r["pid"], "review_no": n, "profile": profile, "stars": review.get("rating", ""), "review_text": redact(collapse(review["content"])), "features": "", "note": ""}
        items.append(item)
        key.append({"item_id": item["item_id"], "system_features": ";".join(system)})
    for label, seed in (("A", 5), ("B", 6)):
        order = list(items)
        random.Random(seed).shuffle(order)
        write(PACK / f"features_sheet_{label}.csv", FEATURE_COLS, order)
    write(PACK / "features_key_private.csv", ["item_id", "system_features"], key)
    write(PACK / "aspect_vocabulary.csv", ["profile", "aspect_id", "label", "kind"], [{"profile": p, "aspect_id": i, "label": v[0], "kind": v[1]} for (p, i), v in sorted(vocabulary.items())])


def instructions() -> str:
    return """# Instructions for annotators

You are helping to check whether an automatic summary of customer reviews is correct. **Work alone. Do not discuss your answers with the other annotator
and do not ask the developers what the system "should" say.** There are no right answers to guess: write what the reviews show. If you are unsure, say so in
`confidence` or `unclear`; that is useful information, not a failure.

Files: `reviews.csv` (every review of every product: stars and text; phone numbers, e-mail addresses, links and handles that people typed into reviews were removed and show as
"[number removed]" and so on), then four sheets, **to be done in this order**:
1. `features_sheet_?.csv` (with `aspect_vocabulary.csv`): list the features each sampled review states. (No system output.)
2. `card_sheet_?.csv`: read the reviews and give your own overall assessment. (No system output is on this sheet.)
3. `claims_sheet_?.csv`: judge each claim. (Only the claim and its quotation are shown.)
4. `words_sheet_?.csv`: rate two anonymous texts. (Do this last: it shows the system's assessment label.)
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

## 4. Features sheet (done FIRST; it is described last because it was added after the others)

Each row is one review. List every product feature the review itself states, from the vocabulary in `aspect_vocabulary.csv` for the row's `profile`, in the form
`aspect_id:positive` or `aspect_id:negative`, separated by semicolons (for example `softness:positive;dryness:negative`). Write `none` if the review states no listed feature
(delivery-only, a bare "ok", a hypothetical, a comparison, something not yet used). A feature counts only if the review says it about the product, in that direction.
Do not add features that are not in the vocabulary; use `note` for them. This sheet measures what the system misses (recall); the claims sheet measures what it gets wrong (precision).

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


def load_provenance(folder: Path) -> dict:
    """Who produced the labels. Scoring refuses without it, so an AI-assisted reference can never be reported as independent human annotation."""
    path = folder / "provenance.json"
    if not path.is_file():
        raise SystemExit(f"{path} is missing. Describe how each label set was produced (see provenance_template.json). Nothing is scored.")
    data = json.loads(path.read_text(encoding="utf-8"))
    single = data.get("mode") == "single_annotation_set"
    if single and data.get("annotator_B") is not None:
        raise SystemExit("provenance.json: mode single_annotation_set requires annotator_B to be null. Nothing is scored.")
    for who in ("annotator_A",) if single else ("annotator_A", "annotator_B"):
        entry = data.get(who) or {}
        missing = [k for k in PROVENANCE_KEYS if not str(entry.get(k, "")).strip()]
        if missing:
            raise SystemExit(f"provenance.json {who}: missing {missing}. Write 'not recorded' if it is unknown. Nothing is scored.")
        if entry["type"] not in ANNOTATOR_TYPES:
            raise SystemExit(f"provenance.json {who}: type must be one of {ANNOTATOR_TYPES}. Nothing is scored.")
    types = {data["annotator_A"]["type"]} | ({data["annotator_B"]["type"]} if not single else set())
    ai = "ai_assisted" in types
    return {
        "mode": "single_annotation_set" if single else "two_annotation_sets",
        "annotator_A": data["annotator_A"],
        "annotator_B": data.get("annotator_B"),
        "independent_of_each_other": data.get("independent_of_each_other", "not stated"),
        "reference_standard": "AI-assisted reference standard (not independent human annotation)" if ai else "human reference standard",
        "independent_human_evaluation_completed": (not ai) and (not single) and data.get("independent_of_each_other") is True,
        "wording_rule": "Report scores as agreement with the AI-assisted reference labels; do not call them human inter-annotator reliability or ground truth." if ai else "",
    }


def parse_features(text: str):
    """'a:positive;b:negative' -> {(a, positive), (b, negative)}; 'none' -> empty set; blank or malformed -> None (row not counted)."""
    text = (text or "").strip().lower()
    if not text:
        return None
    if text == "none":
        return set()
    found = set()
    for part in text.replace("\n", ";").split(";"):
        part = part.strip()
        if not part:
            continue
        name, _, polarity = part.partition(":")
        if polarity.strip() not in ("positive", "negative") or not name.strip():
            return None
        found.add((name.strip(), polarity.strip()))
    return found


def prf(system: list, reference: list) -> dict:
    tp = sum(len(s & r) for s, r in zip(system, reference))
    fp = sum(len(s - r) for s, r in zip(system, reference))
    fn = sum(len(r - s) for s, r in zip(system, reference))
    nan = float("nan")
    precision = tp / (tp + fp) if tp + fp else nan
    recall = tp / (tp + fn) if tp + fn else nan
    f1 = 2 * precision * recall / (precision + recall) if tp else (0.0 if tp + fp + fn else nan)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def score_features(folder: Path):
    """Review-level precision, recall and F1 of the system's (feature, direction) pairs against each annotator, and against the pairs both list."""
    if not (folder / "features_sheet_A.csv").is_file() or not (folder / "features_sheet_B.csv").is_file():
        return None
    key = {r["item_id"]: {tuple(x.split(":")) for x in r["system_features"].split(";") if x} for r in read_rows(PACK / "features_key_private.csv")}
    sheets = {who: {r["item_id"]: parse_features(r["features"]) for r in read_rows(folder / f"features_sheet_{who}.csv")} for who in "AB"}
    ids = sorted(i for i in key if sheets["A"].get(i) is not None and sheets["B"].get(i) is not None)
    if len(ids) < MIN_FEATURE_ITEMS:
        raise SystemExit(f"Features sheets: only {len(ids)} reviews listed by both annotators; at least {MIN_FEATURE_ITEMS} are needed. Nothing is scored.")
    system = [key[i] for i in ids]
    a, b = [sheets["A"][i] for i in ids], [sheets["B"][i] for i in ids]
    out = {
        "reviews": len(ids),
        "reviews_with_a_feature_per_annotator": [sum(bool(x) for x in a), sum(bool(y) for y in b)],
        "system_vs_annotator_A": prf(system, a),
        "system_vs_annotator_B": prf(system, b),
        "system_vs_pairs_both_list": prf(system, [x & y for x, y in zip(a, b)]),
        "system_vs_pairs_either_lists": prf(system, [x | y for x, y in zip(a, b)]),
        "annotator_B_vs_A_as_reference": prf(b, a),
        "target_f1": TARGET_F1,
        "note": "micro-averaged over (review, feature, direction) pairs from a random sample of reviews of the sampled products; "
                "the target is a figure to report against, never a reason to change labels, the sample or the extractor's thresholds",
    }
    f1 = out["system_vs_annotator_A"]["f1"], out["system_vs_annotator_B"]["f1"]
    out["meets_target_against_both_annotators"] = all(v >= TARGET_F1 for v in f1) if all(v == v for v in f1) else None
    return out


def score_single(folder: Path, provenance: dict) -> dict:
    """One annotation set (sheet A only): precision, recall and F1 against that set. Agreement between sets, the card and the words ratings are reported as pending, never filled in."""
    out: dict = {"note": "computed only from the annotator's sheets; developer judgements are not used anywhere", "provenance": provenance}
    pending = "pending: no annotation exists for this section"
    claims_path = folder / "claims_sheet_A.csv"
    if claims_path.is_file():
        rows = [r for r in read_rows(claims_path) if r["label"].strip() in CLAIM_LABELS]
        if len(rows) < MIN_CLAIMS:
            raise SystemExit(f"Claims sheet: only {len(rows)} claims labelled; at least {MIN_CLAIMS} are needed. Nothing is scored.")
        counts = collections.Counter(r["label"].strip() for r in rows)
        n = len(rows)
        good = counts["correct"]
        decided = good + counts["wrong_direction"]
        unsupported = counts["wrong_aspect"] + counts["wrong_direction"] + counts["not_about_the_product"]
        menu = [r for r in rows if "menu-tag" in r.get("note", "").lower()]
        out["claims"] = {
            "claims": n,
            "label_counts": dict(counts),
            "claim_precision_correct_share": [good, n, wilson(good, n)],
            "direction_accuracy_among_claims_about_the_right_aspect": [good, decided, wilson(good, decided)] if decided else "n/a",
            "quotation_does_not_support_the_claim_rate": [unsupported, n, wilson(unsupported, n)],
            "unclear_share": [counts["unclear"], n, wilson(counts["unclear"], n)],
            "claims_whose_quotation_is_a_marketplace_suggestion_list": [len(menu), n],
            "note": "'correct' means the quotation says this about the product in this direction. Claim precision is NOT recall and is not an F1.",
        }
    else:
        out["claims"] = pending
    features = None
    if (folder / "features_sheet_A.csv").is_file():
        key = {r["item_id"]: {tuple(x.split(":")) for x in r["system_features"].split(";") if x} for r in read_rows(PACK / "features_key_private.csv")}
        sheet = {r["item_id"]: r for r in read_rows(folder / "features_sheet_A.csv")}
        ids = sorted(i for i in key if i in sheet and parse_features(sheet[i]["features"]) is not None)
        if len(ids) < MIN_FEATURE_ITEMS:
            raise SystemExit(f"Features sheet: only {len(ids)} reviews labelled; at least {MIN_FEATURE_ITEMS} are needed. Nothing is scored.")
        system = [key[i] for i in ids]
        ref = [parse_features(sheet[i]["features"]) for i in ids]
        plain = [i for i in ids if "menu-tag" not in sheet[i].get("note", "").lower()]
        features = {
            "reviews": len(ids),
            "reviews_with_a_reference_feature": sum(bool(r) for r in ref),
            "system_vs_reference": prf(system, ref),
            "sensitivity_only_reviews_without_a_suggestion_list": {"reviews": len(plain), **prf([key[i] for i in plain], [parse_features(sheet[i]["features"]) for i in plain])},
            "per_direction": {d: prf([{x for x in key[i] if x[1] == d} for i in ids], [{x for x in parse_features(sheet[i]["features"]) if x[1] == d} for i in ids]) for d in ("positive", "negative")},
            "target": TARGET_F1,
            "note": "micro-averaged over (review, feature, direction) pairs from a random sample of reviews; the reference is ONE annotation set and its policy choices (suggestion lists ignored; bare 'ok' and generic praise neutral) are documented in human_evaluation.md",
        }
        out["features"] = features
    else:
        out["features"] = pending
    out["card"] = pending
    out["words"] = pending
    out["agreement_between_annotation_sets"] = "pending: only one annotation set exists"
    return out


def score(folder: Path) -> dict:
    provenance = load_provenance(folder)
    if provenance["mode"] == "single_annotation_set":
        return score_single(folder, provenance)
    key = {r["product_id"]: r for r in read_rows(PACK / "key_private.csv")}
    out: dict = {"note": "computed only from the annotators' sheets; developer judgements are not used anywhere"}
    out["provenance"] = provenance

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
    features = score_features(folder)
    out["features"] = features if features else "no features sheets supplied: recall and F1 are not computed"
    out["claim_f1_note"] = "Precision is reported in 'claims'. Recall and F1 exist only in 'features', where the annotators list what each review states."
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
