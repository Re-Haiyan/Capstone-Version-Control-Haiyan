"""Label statistics behind owner decisions D (missing freebies) and G (thin material, "pero okay"). Training file only.

    D:\\defaketive-train\\Scripts\\python.exe research\\policy_decision_data.py

D: freebie wording split by whether the review says the freebie was promised (a listing or sale promise) and whether it is missing.
G: thin wording with a concession, split by whether the reviewer also names a drawback or worry ("sana tumagal", "kaso", "nga lang",
an intensifier) or only praises. The team-supplied labels' distribution in each cell shows which interpretation they follow.
Teams-supplied labels, provenance unverified. Writes research/results/policy_decision_data.json.
"""
import collections, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import FLAGS6, ROOT, load

rows = load("train_v3")
gold = lambda r: {f for f, v in zip(FLAGS6, r["y"]) if v}


def table(sel):
    c = collections.Counter(f for r in sel for f in (gold(r) or {"none"}))
    n = len(sel)
    return {"rows": n, "labels": dict(c.most_common()), "not_as_described_share": round(c["not_as_described"] / n, 2) if n else None, "quality_share": round(c["quality"] / n, 2) if n else None,
            "none_share": round(c["none"] / n, 2) if n else None}


# D
FREEBIE = re.compile(r"free\s?(?:gift|bie|shirt|tshirt|tumbler|item)|freebies?|libre|regalo", re.I)
MISSING = re.compile(r"(?:wala|walang|no|not|did\s?n.?t|di|hindi|without|kulang|missing)\s+(?:\w+\s+){0,4}(?:free\s?(?:gift|bie|shirt|tshirt|tumbler|item)|freebies?|libre|regalo)|(?:free\s?(?:gift|bie|shirt|tshirt|tumbler|item)|freebies?|libre|regalo)\s+(?:\w+\s+){0,3}(?:wala|missing|none|kulang|hindi|di|not)", re.I)
PROMISED = re.compile(r"nakalagay|nakasulat|advertis\w*|promis\w*|promo|listing|description|sabi\s+(?:sa|ng|nyo|niyo)|sinabi|stated|states|says|supposed|dapat|included\s+daw|daw|as\s+per|per\s+the|in\s+the\s+post|11\.11|12\.12|sale", re.I)
freebie_rows = [r for r in rows if FREEBIE.search(r["text"])]
missing = [r for r in freebie_rows if MISSING.search(r["text"])]
cells = {
    "missing and promised (listing, sale or seller said so)": [r for r in missing if PROMISED.search(r["text"])],
    "missing, no promise stated": [r for r in missing if not PROMISED.search(r["text"])],
    "freebie mentioned, not missing": [r for r in freebie_rows if r not in missing],
}
D = {"all_freebie_rows": table(freebie_rows), **{k: table(v) for k, v in cells.items()}}
D["examples"] = {k: [r["text"][:110] for r in v[:4]] for k, v in cells.items()}

# G
THIN = re.compile(r"manipis|nipis|\bthin\b|payat", re.I)
CONCESSION = re.compile(r"(?:pero|but|though|kaso|however|naman|okay|oks|ok lang|pwede|goods)", re.I)
DRAWBACK = re.compile(r"sana|kaso|nga\s+lang|sayang|tumagal|magtagal|tatagal|madaling|mabilis\s+masira|marupok|di\s+(?:pwede|kaya)|hindi\s+(?:pwede|kaya|matibay)|worry|baka|lang\s+sya\s+pero|medyo\s+(?:manipis|nipis)|sobra|sobrang|masyado|too|very|grabe|parang\s+papel", re.I)
thin_rows = [r for r in rows if THIN.search(r["text"])]
concession = [r for r in thin_rows if CONCESSION.search(r["text"])]
no_concession = [r for r in thin_rows if not CONCESSION.search(r["text"])]
G = {"all_thin_rows": table(thin_rows), "thin_without_a_concession": table(no_concession), "thin_with_a_concession": table(concession),
     "thin_with_a_concession_and_a_named_drawback_or_intensifier": table([r for r in concession if DRAWBACK.search(r["text"])]),
     "thin_with_a_concession_and_no_drawback_named": table([r for r in concession if not DRAWBACK.search(r["text"])])}
G["examples"] = {"concession_no_drawback": [r["text"][:110] for r in concession if not DRAWBACK.search(r["text"])][:5], "concession_with_drawback": [r["text"][:110] for r in concession if DRAWBACK.search(r["text"])][:5]}
json.dump({"D_freebies": D, "G_thin": G}, open(ROOT / "research" / "results" / "policy_decision_data.json", "w"), indent=1, ensure_ascii=False)
print("D freebies:"); [print(f"  {k:60} {v['rows']:3} rows  NAD {v['not_as_described_share']}  none {v['none_share']}  {v['labels']}") for k, v in D.items() if k not in ("examples",)]
print("G thin:"); [print(f"  {k:62} {v['rows']:3} rows  quality {v['quality_share']}  none {v['none_share']}") for k, v in G.items() if k not in ("examples",)]
