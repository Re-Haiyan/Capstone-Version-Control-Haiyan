"""Alternative conclusion policies for a product with no warning signs, and their evaluation. Research code: NOT used by the app.

    backend\\.venv\\Scripts\\python.exe research\\conclusion_policies.py

Today (P0): positive share (neutral counted in the denominator) >= 0.75 and its Wilson lower bound >= 0.65 gives "recommended", >= 0.50
gives "mixed", below 0.50 "not recommended". A review that states no opinion therefore counts against a product exactly like a negative one.

Alternatives, all applied only when the verdict state is no_warning_signs (every other state keeps the current rules):
  P1 opinionated only: shares are computed among reviews that take a side (positive / (positive + negative)); fewer than 20 reviews
     that take a side gives "not enough" (insufficient INFORMATIVE reviews).
  P2 negative-led: "recommended" needs a low negative share (<= 15%) as well as a high positive share among opinionated reviews;
     "not recommended" when negative share >= 40% or positive among opinionated < 50%; otherwise "mixed". Fewer than 20 opinionated: not enough.
  P3 wording only: the same decisions as P0, with a note when many reviews state no opinion.
Evaluated on (a) the existing scenario tests (which decisions they pin), (b) neutral-heavy scenarios, (c) the shadow-mode saved products
(research/results/shadow_sentiment.json: deployed and calibrated shares). No policy is activated and no product-level accuracy exists to judge
which is right; this shows only how each behaves.
"""
import collections, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment.proportions import wilson_lower_bound  # noqa: E402

RECOMMEND_SHARE, RECOMMEND_BOUND, MIXED_SHARE = 0.75, 0.65, 0.50
MIN_INFORMATIVE = 20


def p0(pos, neu, neg, usable, bound=None):
    total = pos + neu + neg
    if total <= 0:
        return None
    share = pos / total
    bound = wilson_lower_bound(round(pos), round(usable)) if bound is None else bound
    if share >= RECOMMEND_SHARE and bound >= RECOMMEND_BOUND:
        return "recommended"
    return "mixed" if share >= MIXED_SHARE else "not_recommended"


def opinionated(pos, neu, neg, usable):
    total = pos + neu + neg
    informative = (pos + neg) / total * usable if total > 0 else 0
    return informative, (pos / (pos + neg) if pos + neg > 0 else None)


def p1(pos, neu, neg, usable, bound=None):
    informative, share = opinionated(pos, neu, neg, usable)
    if share is None or informative < MIN_INFORMATIVE:
        return "not_enough"
    lb = wilson_lower_bound(round(share * informative), round(informative))
    if share >= RECOMMEND_SHARE and lb >= RECOMMEND_BOUND:
        return "recommended"
    return "mixed" if share >= MIXED_SHARE else "not_recommended"


def p2(pos, neu, neg, usable, bound=None):
    informative, share = opinionated(pos, neu, neg, usable)
    total = pos + neu + neg
    if share is None or informative < MIN_INFORMATIVE:
        return "not_enough"
    neg_share = neg / total
    lb = wilson_lower_bound(round(share * informative), round(informative))
    if neg_share >= 0.40 or share < MIXED_SHARE:
        return "not_recommended"
    if neg_share <= 0.15 and share >= RECOMMEND_SHARE and lb >= RECOMMEND_BOUND:
        return "recommended"
    return "mixed"


def p3(pos, neu, neg, usable, bound=None):
    return p0(pos, neu, neg, usable, bound)


POLICIES = {"P0 today": p0, "P1 opinionated only": p1, "P2 negative-led": p2, "P3 wording only": p3}

# (a) the scenarios pinned by tests/test_conclusion.py for a product with no warning signs: (positive, uncertain, negative, usable, bound, expected today)
PINNED = [("85 positive, 5 uncertain, 10 negative (bound .78)", 85, 5, 10, 100, 0.78, "recommended"),
          ("9 of 10 positive, small sample (bound .6)", 9, 0, 1, 10, 0.6, "mixed"),
          ("60 / 10 / 30", 60, 10, 30, 100, None, "mixed"),
          ("30 / 10 / 60", 30, 10, 60, 100, None, "not_recommended"),
          ("weighted shares 90 / 5 / 5 (bound .8)", 90, 5, 5, 100, 0.8, "recommended")]
# (b) neutral-heavy scenarios (percent, usable 100)
NEUTRAL_HEAVY = [("75 / 15 / 10", 75, 15, 10), ("70 / 20 / 10", 70, 20, 10), ("65 / 30 / 5", 65, 30, 5), ("60 / 35 / 5", 60, 35, 5), ("50 / 40 / 10", 50, 40, 10),
                 ("40 / 40 / 20", 40, 40, 20), ("45 / 25 / 30", 45, 25, 30), ("30 / 60 / 10", 30, 60, 10), ("10 / 85 / 5", 10, 85, 5), ("20 / 60 / 20", 20, 60, 20)]
out = {"pinned_scenarios": [], "neutral_heavy": [], "shadow_products": {}}
print("(a) scenarios pinned by the existing tests (no warning signs)")
for name, pos, neu, neg, usable, bound, expected in PINNED:
    row = {n: f(pos, neu, neg, usable, bound) for n, f in POLICIES.items()}
    row["scenario"] = name; row["pinned_by_tests_today"] = expected; out["pinned_scenarios"].append(row)
    print(f"  {name:48} today pinned: {expected:16} | " + " | ".join(f"{n.split()[0]} {v}" for n, v in row.items() if n.startswith("P")))
print("\n(b) neutral-heavy scenarios (positive / uncertain / negative, 100 usable reviews)")
for name, pos, neu, neg in NEUTRAL_HEAVY:
    row = {n: f(pos, neu, neg, 100) for n, f in POLICIES.items()}; row["scenario"] = name; out["neutral_heavy"].append(row)
    print(f"  {name:14} " + " | ".join(f"{n.split()[0]} {v}" for n, v in row.items()))
shadow = json.load(open(ROOT / "research" / "results" / "shadow_sentiment.json"))["products"]
print("\n(c) the 60 saved products, deployed sentiment and calibrated sentiment (decision counts, and changes against 'P0 with deployed sentiment')")
for source in ("deployed", "calibrated"):
    for name, f in POLICIES.items():
        decisions = []
        for p in shadow:
            pos, neu, neg = p[f"positive_{source}"], p[f"neutral_{source}"], p[f"negative_{source}"]
            decisions.append(f(pos, neu, neg, p["usable"], p[f"lower_bound_{source}"]))
        out["shadow_products"][f"{name} | {source} sentiment"] = dict(collections.Counter(decisions))
base = [p0(p["positive_deployed"], p["neutral_deployed"], p["negative_deployed"], p["usable"], p["lower_bound_deployed"]) for p in shadow]
for source in ("deployed", "calibrated"):
    for name, f in POLICIES.items():
        dec = [f(p[f"positive_{source}"], p[f"neutral_{source}"], p[f"negative_{source}"], p["usable"], p[f"lower_bound_{source}"]) for p in shadow]
        changed = sum(1 for a, b in zip(base, dec) if a != b)
        print(f"  {name:22} | {source:10} sentiment: {dict(collections.Counter(dec))}  changed vs today: {changed} of {len(shadow)}")
        out["shadow_products"][f"{name} | {source} sentiment | changed_vs_today"] = changed
json.dump(out, open(ROOT / "research" / "results" / "conclusion_policy_eval.json", "w"), indent=1)
