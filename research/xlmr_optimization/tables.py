"""Assemble markdown tables from results/metrics__*.json (every number in the reports traces to those files).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/tables.py [model ...]     (default: every model with metrics)
Writes results/tables.md and prints it.
"""
import glob, json, pathlib, sys

X = pathlib.Path(__file__).resolve().parent
SETS = ["firecs_test", "market_test_v3", "market_gold200", "market_heldout100", "market_val", "firecs_val"]
NOTE = {"firecs_test": "FiReCS test (published labels; used to gate the shipped model)", "market_test_v3": "historical benchmark, team labels (inspected)",
        "market_gold200": "older team-labelled 200 (150 high confidence)", "market_heldout100": "older team-labelled 100 (76 high)",
        "market_val": "marketplace VALIDATION split (36 products held out of fine-tuning; selection set)", "firecs_val": "FiReCS validation split"}


def main(models):
    data = {}
    for f in glob.glob(str(X / "results" / "metrics__*.json")):
        d = json.load(open(f))
        data[(d["model"], d["set"])] = d
    names = models or sorted({m for m, _ in data})
    out = []
    for s in SETS:
        rows = [(m, data[(m, s)]) for m in names if (m, s) in data]
        if not rows:
            continue
        out.append(f"\n### {s}: {NOTE[s]}\n\n| Model | n | Accuracy | Macro F1 (95% interval) | Negative F1 | Neutral F1 | Positive F1 | Negative recall |\n|---|---:|---:|---|---:|---:|---:|---:|")
        for m, d in rows:
            c = d["classes"]
            ci = d.get("macro_f1_ci95_product_bootstrap") or d.get("macro_f1_ci95_row_bootstrap")
            out.append(f"| {m} | {d['rows_scored']} | {d['accuracy']:.3f} | {d['macro_f1']:.3f} ({ci[0]:.3f} to {ci[1]:.3f}) | {c['negative']['f1']:.3f} | {c['neutral']['f1']:.3f} | {c['positive']['f1']:.3f} | {c['negative']['recall']:.3f} |")
    text = "\n".join(out)
    (X / "results" / "tables.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main(sys.argv[1:])
