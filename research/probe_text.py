import sys, os, json
for k in [k for k in os.environ if k.startswith("DEFAKETIVE_")]: del os.environ[k]
sys.path.insert(0, sys.argv[1] + "/backend/sentiment-analysis")
from defaketive_sentiment import registry
m = registry.load_model()
prod = sys.argv[2]
for line in open(sys.argv[3], encoding="utf-8"):
    line = line.strip()
    if not line: continue
    a = m.analyze_batch([line], [3], listing={"name": prod})[0]
    s = a["sentences"][0] if a["sentences"] else {}
    print(("SAFETY " if "safety" in a["review_tags"] else "no     "), a["review_tags"], "|", line[:110], "|", [(t["category"], t.get("excluded")) for t in s.get("terms", []) if t["category"] == "safety"])
