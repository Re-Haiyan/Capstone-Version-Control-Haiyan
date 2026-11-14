"""Per-label scores of the rules on the fit rows and the validation rows (cut by product), and the fit-row errors.

    python training/rules_errors.py predictions.json labelled.csv [label] [fp|fn] [how many]
"""
import csv, hashlib, json, sys
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality")
pred = json.load(open(sys.argv[1])); rows = [r for r in csv.DictReader(open(sys.argv[2], encoding="utf-8-sig")) if r["id"] in pred]
key = {}
import pathlib
kp = pathlib.Path(sys.argv[2]).with_name(pathlib.Path(sys.argv[2]).stem + "_key.csv")
if kp.is_file(): key = {r["id"]: r for r in csv.DictReader(open(kp, encoding="utf-8-sig"))}
def is_valid(r): return int(hashlib.md5(("valid" + " ".join(r["product"].split())).encode()).hexdigest(), 16) % 100 < 12
def gold(r): return {f for f in r["flags"].replace(" ", "").split(";")}
def table(name, subset):
    print(f"{name} ({len(subset)} rows)")
    for k, f in enumerate(FLAGS):
        tp = sum(1 for r in subset if f in gold(r) and pred[r["id"]]["pred"][k]); fp = sum(1 for r in subset if f not in gold(r) and pred[r["id"]]["pred"][k]); fn = sum(1 for r in subset if f in gold(r) and not pred[r["id"]]["pred"][k])
        P = tp / (tp + fp) if tp + fp else 0; R = tp / (tp + fn) if tp + fn else 0; F = 2 * P * R / (P + R) if P + R else 0
        print(f"  {f:17} n+={tp+fn:4} tp={tp:4} fp={fp:4} fn={fn:4}  P {P:.2f} R {R:.2f} F1 {F:.2f}")
fit = [r for r in rows if not is_valid(r)]; valid = [r for r in rows if is_valid(r)]
table("FIT", fit); table("VALID", valid)
if len(sys.argv) > 3:
    f = sys.argv[3]; kind = sys.argv[4]; n = int(sys.argv[5]) if len(sys.argv) > 5 else 40; k = FLAGS.index(f)
    errs = [r for r in fit if (kind == "fp" and f not in gold(r) and pred[r["id"]]["pred"][k]) or (kind == "fn" and f in gold(r) and not pred[r["id"]]["pred"][k])]
    print(f"\n{f} {kind}: {len(errs)} on fit rows")
    for r in errs[:n]:
        print(f"[{(key.get(r['id']) or {}).get('category','')}] ({r['product'][:28]}) gold={r['flags'][:30]} | {r['review_text'][:150]}")
