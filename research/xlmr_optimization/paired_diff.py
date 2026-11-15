"""Paired bootstrap of the macro-F1 difference between two prediction files on the same rows (product-grouped where the set has products).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/paired_diff.py <candidate tag> <baseline tag> <set> [<set> ...]
The interval says how much the difference moves when products are resampled. It is NOT a significance claim for new data: the historical benchmark was inspected,
the labels are unverified, and the candidate was chosen with other data of the same kind.
"""
import csv, json, pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata, metrics_x  # noqa: E402
from inference import rows_of  # noqa: E402
cand, base = sys.argv[1], sys.argv[2]
for name in sys.argv[3:]:
    rows = {r["id"]: r for r in rows_of(name)}
    A = {r["id"]: r["pred"] for r in csv.DictReader(open(xdata.X / "predictions" / f"{cand}__{name}.csv"))}
    B = {r["id"]: r["pred"] for r in csv.DictReader(open(xdata.X / "predictions" / f"{base}__{name}.csv"))}
    ids = [i for i in A if rows[i]["conf"] in ("high", "published")]
    y = np.array([xdata.LABELS.index(rows[i]["label"]) for i in ids]); a = np.array([xdata.LABELS.index(A[i]) for i in ids]); b = np.array([xdata.LABELS.index(B[i]) for i in ids])
    groups = np.array([rows[i]["product"] or i for i in ids]); keys = np.unique(groups); index = {k: np.where(groups == k)[0] for k in keys}
    rng = np.random.default_rng(0); d = []
    for _ in range(1000):
        idx = np.concatenate([index[k] for k in rng.choice(keys, len(keys))])
        d.append(metrics_x.macro(y[idx], a[idx]) - metrics_x.macro(y[idx], b[idx]))
    diff = metrics_x.macro(y, a) - metrics_x.macro(y, b)
    out = {"candidate": cand, "baseline": base, "set": name, "n": len(ids), "macro_f1_difference": diff, "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], "grouping": "product" if any(rows[i]["product"] for i in ids) else "row"}
    json.dump(out, open(xdata.X / "results" / f"paired__{cand}__vs__{base}__{name}.json", "w"), indent=1)
    print(f"{cand} vs {base} on {name} (n={len(ids)}, {out['grouping']} bootstrap): macro F1 difference {diff:+.3f}  95% interval {out['ci95'][0]:+.3f} to {out['ci95'][1]:+.3f}")
