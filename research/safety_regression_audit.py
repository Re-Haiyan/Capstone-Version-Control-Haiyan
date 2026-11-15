"""Build research/safety_regression_audit.csv: the reviews that lose their safety flag between production (d74589a) and the release candidate.

    python research/safety_probe.py <old_checkout> ids.json . old.json      (and again for the new checkout -> new.json)
    python research/safety_regression_audit.py ids.json old.json new.json

For each review: the text, the product and its group, the old and new safety decision with the rule that made it, the reader's
assessment of whether it describes a genuine hazard, and whether independent adjudication is still needed. The assessment is one
reader's (not an annotation); the team-supplied label is shown only for information and is not treated as correct.
"""
import csv, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
ids = json.load(open(sys.argv[1])); old = json.load(open(sys.argv[2])); new = json.load(open(sys.argv[3]))
rows, keys = {}, {}
for name in ("train_v3", "test_v3"):
    for r in csv.DictReader(open(HERE / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")): rows[r["id"]] = r
    for r in csv.DictReader(open(HERE / "evaluation/annotated" / f"{name}_key.csv", encoding="utf-8-sig")): keys[r["id"]] = r

RULES = [
    ("feature claim", re.compile(r"prevents? collapse", re.I),
     "product_category.py _FEATURE_CLAIM ('prevents collapse': a product feature written in a listing, not a report)",
     "No: a listing feature line (boilerplate) on a baby-bottle product; no event is described", "No"),
    ("burn exemption", re.compile(r"calori\w+(?:\s+\w+){0,2}\s+burn|burn(?:ed|t)?\s+calori|na burn|burn test", re.I),
     "lexicons/categories/all.tsv row 'burning calories or a burn test is not a fire hazard' (exempt when calorie/test/workout/steps are near)",
     "No: calories burned (fitness tracking) or a monitor burn-in test; no heat or fire event", "No"),
    ("itch claim", re.compile(r"relieves itching", re.I),
     "lexicons/categories/all.tsv row 'what the product treats, not a reaction to it' (relieve/treat/soothe near itch/rash)",
     "No: the product's advertised benefit (relieves itching); no skin reaction to the product is described", "No"),
    ("date", re.compile(r"expired date", re.I),
     "product_category.py _PRAISE_SAFE (a stated expiry date is not an expired item), now guarded by _EXPIRED_REPORT",
     "Probably not: the reviewer complains the expiry date is too early (short shelf life), and does not say the item was expired or spoiled; but the review date is unknown and a September 2026 date may already have passed when it arrived",
     "YES: ambiguous; needs a human to say whether this is a short shelf life (not a hazard) or an item that arrived expired"),
]
out = []
for i in ids:
    r = rows[i]; text = r["review_text"]
    o_sent = [s for s in old[i]["sentences"] if "safety" in s["tags"]]
    old_rule = "; ".join(sorted({f"keyword '{t['ngram'][:28]}...' (learned {s['learned'].get('safety')})" for s in o_sent for t in s["terms"] if t["category"] == "safety"})) or "learned classifier only"
    n_sent = [s for s in new[i]["sentences"] if any(t["category"] == "safety" and t.get("excluded") for t in s["terms"])]
    hit = [x for x in RULES if x[1].search(text)]
    assert len(hit) == 1, (i, [h[0] for h in hit])
    name, _, rule, genuine, adjud = hit[0]
    out.append({
        "id": i, "product": r["product"], "group": keys[i]["group"], "stars": r["stars"], "review_text": text.replace("\n", " ")[:500],
        "old_safety_decision": "flagged: " + old_rule, "new_safety_decision": "not flagged (term excluded: " + ", ".join(sorted({t.get('excluded') for s in n_sent for t in s['terms'] if t.get('excluded')})) + "; learned safety score " + str(min((s.get('learned') or {}).get('safety', 0) for s in n_sent) if n_sent else "n/a") + ")",
        "rule_responsible": rule, "describes_genuine_hazard": genuine, "needs_human_adjudication": adjud, "team_label_for_information_only": r["flags"],
    })
with open(HERE / "research" / "safety_regression_audit.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
from collections import Counter
print(len(out), Counter(o["rule_responsible"][:40] for o in out), "| needing adjudication:", sum(o["needs_human_adjudication"].startswith("YES") for o in out))
