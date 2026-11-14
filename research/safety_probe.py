import json, sys, os, pathlib, csv
root = pathlib.Path(sys.argv[1])
for k in [k for k in os.environ if k.startswith("DEFAKETIVE_")]: del os.environ[k]
sys.path.insert(0, str(root / "backend" / "sentiment-analysis"))
from defaketive_sentiment import registry
m = registry.load_model()
ids = json.load(open(sys.argv[2]))
here = pathlib.Path(sys.argv[3])
rows = {}
for name in ("train_v3", "test_v3"):
    for r in csv.DictReader(open(here / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")):
        rows[r["id"]] = r
out = {}
for i in ids:
    r = rows[i]
    a = m.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]})[0]
    out[i] = {k: a.get(k) for k in a if k in ("sentences","review_tags","review_extra_tags","review_terms","review_scores","review_category","product_category","review_evidence","review_evidence_dropped","label")}
    out[i]["_keys"] = sorted(a.keys())
json.dump(out, open(sys.argv[4], "w"), default=str)
