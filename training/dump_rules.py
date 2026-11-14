"""Rule flags (the deployed checker, with the product title) for the rows in probs.json."""
import csv, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import registry
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality")
run = pathlib.Path(sys.argv[1]); probs = json.load(open(run / "probs.json"))
rows = {}
files = sys.argv[2:] or ["evaluation/annotated/train_all.csv", "evaluation/annotated/test_all.csv"]
for f in files:
    for r in csv.DictReader(open(ROOT / f, encoding="utf-8-sig")): rows[r["id"]] = r
model = registry.load_model(); out = {}
for part in ("valid", "test"):
    for item in probs[part]:
        r = rows[item["id"]]
        a = model.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]})[0]
        tags = set(a.get("review_tags") or []) | set(a.get("review_extra_tags") or [])
        out[item["id"]] = [1 if f in tags else 0 for f in FLAGS]
json.dump(out, open(run / "rules.json", "w"))
print(len(out))
