"""Experiment F: probability calibration and a decision rule, fitted on the marketplace VALIDATION split only, applied unchanged to the other sets.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/calibrate.py <model tag> [<model tag> ...]

For each tag with predictions/<tag>__market_val.csv: (1) temperature scaling (minimise validation log-loss; it never changes a label, so F1 is unchanged and only
calibration moves), (2) a neutral-bias decision rule (add b to the neutral log-probability, b chosen on validation macro F1 from a grid), reported on every other set the
tag has predictions for. Marketplace validation is 495 rows of 36 products with unverified labels: the choice of b is noisy, so the result is evidence about
direction, not a tuned optimum. Writes results/calibration__<tag>.json.
"""
import csv, json, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata, metrics_x  # noqa: E402
from inference import rows_of  # noqa: E402

L = xdata.LABELS


def load(tag, name):
    path = xdata.X / "predictions" / f"{tag}__{name}.csv"
    if not path.exists():
        return None
    rows = {r["id"]: r for r in rows_of(name)}
    pred = [p for p in csv.DictReader(open(path, encoding="utf-8")) if rows[p["id"]]["conf"] in ("high", "published")]
    y = np.array([L.index(rows[p["id"]]["label"]) for p in pred])
    P = np.array([[float(p["p_neg"]), float(p["p_neu"]), float(p["p_pos"])] for p in pred])
    return y, np.clip(P, 1e-9, 1.0)


def nll(P, y):
    return float(-np.log(P[np.arange(len(y)), y]).mean())


def ece(P, y, bins=15):
    conf, pred = P.max(1), P.argmax(1)
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            total += m.mean() * abs((pred[m] == y[m]).mean() - conf[m].mean())
    return float(total)


def soft(logits):
    z = logits - logits.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def run(tag):
    val = load(tag, "market_val")
    if val is None:
        return None
    yv, Pv = val
    lv = np.log(Pv)
    temps = np.arange(0.5, 4.01, 0.05)
    T = float(temps[int(np.argmin([nll(soft(lv / t), yv) for t in temps]))])
    best_b, best_f = 0.0, -1.0
    for b in np.arange(-1.0, 2.01, 0.1):
        f = metrics_x.macro(yv, (lv + np.array([0, b, 0])).argmax(1))
        if f > best_f + 1e-9:
            best_b, best_f = float(b), f
    out = {"tag": tag, "temperature": T, "neutral_bias": best_b, "validation_macro_f1_at_bias": best_f, "sets": {}}
    for name in ("market_val", "market_test_v3", "market_gold200", "market_heldout100", "firecs_test", "firecs_val"):
        got = load(tag, name)
        if got is None:
            continue
        y, P = got
        l = np.log(P)
        s = metrics_x.summarize(y, P.argmax(1))
        sb = metrics_x.summarize(y, (l + np.array([0, best_b, 0])).argmax(1))
        Pt = soft(l / T)
        out["sets"][name] = {"n": int(len(y)), "before": {"macro_f1": s["macro_f1"], "neutral_f1": s["classes"]["neutral"]["f1"], "negative_recall": s["classes"]["negative"]["recall"], "nll": nll(P, y), "ece": ece(P, y)},
                             "temperature_scaled": {"macro_f1": s["macro_f1"], "nll": nll(Pt, y), "ece": ece(Pt, y)},
                             "neutral_bias_rule": {"macro_f1": sb["macro_f1"], "neutral_f1": sb["classes"]["neutral"]["f1"], "negative_recall": sb["classes"]["negative"]["recall"], "positive_f1": sb["classes"]["positive"]["f1"]}}
    json.dump(out, open(xdata.X / "results" / f"calibration__{tag}.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        o = run(tag)
        if not o:
            print(tag, "no validation predictions"); continue
        print(f"\n{tag}: temperature {o['temperature']:.2f}, neutral bias {o['neutral_bias']:+.1f} (validation macro F1 {o['validation_macro_f1_at_bias']:.3f})")
        for n, v in o["sets"].items():
            b, t, r = v["before"], v["temperature_scaled"], v["neutral_bias_rule"]
            print(f"  {n:<18} n={v['n']:<5} macroF1 {b['macro_f1']:.3f} -> bias rule {r['macro_f1']:.3f} (neutral F1 {b['neutral_f1']:.3f} -> {r['neutral_f1']:.3f}, neg recall {b['negative_recall']:.3f} -> {r['negative_recall']:.3f}) | NLL {b['nll']:.3f} -> {t['nll']:.3f}, ECE {b['ece']:.3f} -> {t['ece']:.3f}")
