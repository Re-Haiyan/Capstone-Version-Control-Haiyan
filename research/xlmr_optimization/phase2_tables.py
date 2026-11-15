"""Tables of the neutral strategy comparison from results/neutral_strategies.json: per-class report and confusion matrices (development validation and cross-validation).

    python research/xlmr_optimization/phase2_tables.py
Writes phase2/strategy_per_class_report.csv and phase2/strategy_confusion_matrices.csv. Development scores only; none of these is final-test performance.
"""
import csv, json, pathlib

X = pathlib.Path(__file__).resolve().parent
d = json.load(open(X / "results/neutral_strategies.json"))
L = ("negative", "neutral", "positive")
NAMES = {"S0": "S0 baseline head", "S1": "S1 class-weighted", "S2": "S2 balanced resampling", "S3": "S3 neutral hard-example mining", "S4": "S4 bias calibration", "S5": "S5 weighted + mining + calibration"}
with open(X / "phase2/strategy_per_class_report.csv", "w", newline="") as f, open(X / "phase2/strategy_confusion_matrices.csv", "w", newline="") as g:
    w, v = csv.writer(f), csv.writer(g)
    w.writerow(["strategy", "C", "evaluation", "n", "class", "precision", "recall", "f1", "support", "accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1"])
    v.writerow(["strategy", "C", "evaluation", "true", "pred_negative", "pred_neutral", "pred_positive"])
    for key, res in d["strategies"].items():
        s, c = key.split("_C")
        for ev in ("dev_market", "dev_ai_pool", "cv_market", "cv_ai_pool", "cv_firecs", "cv_all"):
            t = res[ev]
            for k in L:
                cl = t["classes"][k]
                w.writerow([NAMES[s], c, ev, t["n"], k, f"{cl['precision']:.3f}", f"{cl['recall']:.3f}", f"{cl['f1']:.3f}", cl["support"], f"{t['accuracy']:.3f}", f"{t['macro_precision']:.3f}", f"{t['macro_recall']:.3f}", f"{t['macro_f1']:.3f}", f"{t['weighted_f1']:.3f}"])
            for i, k in enumerate(L):
                v.writerow([NAMES[s], c, ev, k, *t["confusion"][i]])
print("written")
