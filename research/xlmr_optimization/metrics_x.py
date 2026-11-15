"""Metrics for sentiment predictions: accuracy, macro/weighted/micro F1, per class P/R/F1/support, confusion matrix, group bootstrap, subgroups.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/metrics_x.py <predictions.csv> [more.csv ...]

Marketplace sets are scored on high-confidence rows (the team's own confidence column); their labels are of UNVERIFIED provenance.
Intervals: bootstrap over PRODUCTS where the product is known (marketplace), over rows for FiReCS (no product field: a row bootstrap
is optimistic about independence and is labelled as such).
"""
import csv, json, pathlib, re, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata  # noqa: E402

L = xdata.LABELS
TL = set("ang ng sa na ko mo po yung ung ay mga hindi naman lang din pero kasi si ni nyo niyo ako ito iyan yan dito talaga sobra sobrang mas pa nang may wala walang di ba ka ako nyo namin natin kayo sila".split())
EN = set("the and is it was very good with for but not this that of to in my you are have had so too bad great love item product quality seller delivery fast".split())


def lang_of(text: str) -> str:
    words = re.findall(r"[a-zñ']+", text.lower())
    if len(words) < 4:
        return "unknown (under 4 words)"
    t = sum(w in TL for w in words); e = sum(w in EN for w in words)
    if t >= 2 and e >= 2:
        return "taglish"
    if t >= 2:
        return "filipino"
    if e >= 2:
        return "english"
    return "unknown"


def prf(y, p, k):
    tp = int(((y == k) & (p == k)).sum()); fp = int(((y != k) & (p == k)).sum()); fn = int(((y == k) & (p != k)).sum())
    pr = tp / (tp + fp) if tp + fp else 0.0; rc = tp / (tp + fn) if tp + fn else 0.0
    return pr, rc, (2 * pr * rc / (pr + rc) if pr + rc else 0.0), int((y == k).sum())


def macro(y, p):
    return float(np.mean([prf(y, p, k)[2] for k in range(3)]))


def summarize(y, p):
    out = {"n": int(len(y)), "accuracy": float((y == p).mean()), "macro_f1": macro(y, p), "micro_f1": float((y == p).mean()),
           "weighted_f1": float(sum(prf(y, p, k)[2] * (y == k).sum() for k in range(3)) / max(1, len(y))), "classes": {}}
    for k, name in enumerate(L):
        pr, rc, f, s = prf(y, p, k)
        out["classes"][name] = {"precision": pr, "recall": rc, "f1": f, "support": s}
    out["confusion"] = [[int(((y == a) & (p == b)).sum()) for b in range(3)] for a in range(3)]
    return out


def boot(y, p, groups, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    g = np.array(groups); keys = np.unique(g); index = {k: np.where(g == k)[0] for k in keys}
    vals = []
    for _ in range(n):
        pick = rng.choice(keys, len(keys))
        idx = np.concatenate([index[k] for k in pick])
        vals.append(macro(y[idx], p[idx]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return [float(lo), float(hi)]


def evaluate(path, high_only=True):
    path = pathlib.Path(path)
    model, name = path.stem.split("__", 1)
    from inference import rows_of
    rows = {r["id"]: r for r in rows_of(name)}
    pred = list(csv.DictReader(open(path, encoding="utf-8")))
    keep = [r for r in pred if (not high_only or rows[r["id"]]["conf"] in ("high", "published"))]
    y = np.array([L.index(rows[r["id"]]["label"]) for r in keep]); p = np.array([L.index(r["pred"]) for r in keep])
    out = {"model": model, "set": name, "rows_scored": len(keep), "rows_excluded_low_confidence": len(pred) - len(keep), **summarize(y, p)}
    products = [rows[r["id"]]["product"] for r in keep]
    if any(products):
        out["macro_f1_ci95_product_bootstrap"] = boot(y, p, products); out["products"] = len(set(products)); out["interval_kind"] = "product bootstrap"
    else:
        out["macro_f1_ci95_row_bootstrap"] = boot(y, p, list(range(len(y))), n=300); out["interval_kind"] = "row bootstrap (no product field; optimistic)"
    out["subgroups"] = {}
    for label, fn in (("language(heuristic)", lambda r: lang_of(rows[r["id"]]["text"])), ("product_group", lambda r: rows[r["id"]]["group"] or "n/a")):
        buckets = {}
        for i, r in enumerate(keep):
            buckets.setdefault(fn(r), []).append(i)
        out["subgroups"][label] = {k: {"n": len(v), "accuracy": float((y[v] == p[v]).mean()), "macro_f1": macro(y[v], p[v]),
                                       "negative_recall": prf(y[v], p[v], 0)[1], "neutral_f1": prf(y[v], p[v], 1)[2]} for k, v in sorted(buckets.items()) if len(v) >= 20}
    cm = xdata.X / "confusion_matrices" / f"{path.stem}.csv"
    with open(cm, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["true\predicted", *L]); [w.writerow([L[i], *out["confusion"][i]]) for i in range(3)]
    return out


if __name__ == "__main__":
    for path in sys.argv[1:]:
        r = evaluate(path)
        target = xdata.X / "results" / f"metrics__{pathlib.Path(path).stem}.json"
        json.dump(r, open(target, "w"), indent=1)
        c = r["classes"]
        print(f"{r['model']:>12} {r['set']:<18} n={r['rows_scored']:<5} acc {r['accuracy']:.3f} macroF1 {r['macro_f1']:.3f} | neg {c['negative']['f1']:.3f} (R {c['negative']['recall']:.3f}) neu {c['neutral']['f1']:.3f} pos {c['positive']['f1']:.3f}")
