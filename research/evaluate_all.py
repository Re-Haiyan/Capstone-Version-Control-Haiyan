"""Full evaluation of the rules, the sparse model and fusions, with product-bootstrap uncertainty.

    D:\\defaketive-train\\Scripts\\python.exe research\\evaluate_all.py

Protocol:
  * Models are trained on the training file only (research/exp_tfidf.py caches out-of-fold and test probabilities).
  * Thresholds: ONE per flag, from a small grid, chosen on the product-grouped out-of-fold predictions of the training file.
  * Fusion strategy per flag (rules / model / OR / AND): chosen on the VALIDATION slice (12% of training products, never
    read for rule tuning), not on the historical test.
  * The historical test (846 rows, inspected during earlier development) is scored once per candidate and is REPORTED, not used to select.
  * Uncertainty: 95% product-bootstrap intervals for F1; paired product-bootstrap interval for the difference from the rules.
Writes research/results/evaluation_all.json and prints a table.
"""
import hashlib, json, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, FLAGS5, FLAGS6, ROOT, best_threshold, load, paired_bootstrap_diff, prf, product_bootstrap_f1, rules_predictions, wilson

train, test = load("train_v3"), load("test_v3")
Y, Yt = np.array([r["y"] for r in train]), np.array([r["y"] for r in test])
oof = np.load(CACHE / "oof_tfidf.npy"); pt = np.load(CACHE / "test_prob_tfidf.npy")
R = rules_predictions("train"); Rt = rules_predictions("test")
rule_tr = np.array([R[r["id"]]["pred"] for r in train]); rule_te = np.array([Rt[r["id"]]["pred"] for r in test])
is_valid = np.array([int(hashlib.md5(("valid" + r["product"]).encode()).hexdigest(), 16) % 100 < 12 for r in train])
out = {"validation_rows": int(is_valid.sum()), "test_rows": len(test), "flags": {}}
table = []
for k, f in enumerate(FLAGS5):
    thr = best_threshold(Y[:, k], oof[:, k])
    m_tr = (oof[:, k] >= thr).astype(int); m_te = (pt[:, k] >= thr).astype(int)
    cands = {"rules": (rule_tr[:, k], rule_te[:, k]), "sparse_model": (m_tr, m_te),
             "rules_OR_model": (np.maximum(rule_tr[:, k], m_tr), np.maximum(rule_te[:, k], m_te)),
             "rules_AND_model": (np.minimum(rule_tr[:, k], m_tr), np.minimum(rule_te[:, k], m_te))}
    val_scores = {n: prf(Y[is_valid, k], c[0][is_valid])["f1"] for n, c in cands.items()}
    # prefer the simpler rules unless a fusion beats them on validation by 0.03
    pick = "rules"
    for n in ("sparse_model", "rules_OR_model", "rules_AND_model"):
        if val_scores[n] >= val_scores[pick] + 0.03:
            pick = n
    entry = {"threshold_one_per_flag": thr, "validation_f1": {n: round(v, 3) for n, v in val_scores.items()}, "selected_on_validation": pick, "historical_test": {}}
    for n, (c_tr, c_te) in cands.items():
        s = prf(Yt[:, k], c_te); lo, hi = product_bootstrap_f1(test, c_te, k, 1000)
        d = paired_bootstrap_diff(test, c_te, rule_te[:, k], k, 1000) if n != "rules" else (0, 0, 0)
        rlo, rhi = wilson(s["tp"], s["support"])
        entry["historical_test"][n] = {**{x: (round(v, 3) if isinstance(v, float) else v) for x, v in s.items()}, "f1_ci95": [round(lo, 3), round(hi, 3)],
                                       "recall_wilson95": [round(rlo, 3), round(rhi, 3)], "f1_minus_rules_ci95": [round(d[0], 3), round(d[2], 3)]}
    out["flags"][f] = entry
    sel = entry["historical_test"][pick]; ru = entry["historical_test"]["rules"]
    table.append((f, ru, pick, sel, entry["historical_test"]["sparse_model"]))
# macro / micro on the historical test for rules and the selected strategy
def assemble(kind):
    cols = []
    for k, f in enumerate(FLAGS5):
        pick = out["flags"][f]["selected_on_validation"] if kind == "selected" else "rules"
        thr = out["flags"][f]["threshold_one_per_flag"]; m_te = (pt[:, k] >= thr).astype(int); r = rule_te[:, k]
        cols.append({"rules": r, "sparse_model": m_te, "rules_OR_model": np.maximum(r, m_te), "rules_AND_model": np.minimum(r, m_te)}[pick])
    return np.stack(cols, axis=1)
for kind in ("rules", "selected"):
    P = assemble(kind); per = [prf(Yt[:, k], P[:, k]) for k in range(5)]
    tp = sum(s["tp"] for s in per); fp = sum(s["fp"] for s in per); fn = sum(s["fn"] for s in per)
    out[f"{kind}_macro_f1"] = round(float(np.mean([s["f1"] for s in per])), 3); out[f"{kind}_micro_f1"] = round(2 * tp / (2 * tp + fp + fn), 3)
# per product group (rules)
groups = {}
for g in sorted({r["group"] for r in test}):
    idx = [i for i, r in enumerate(test) if r["group"] == g]
    groups[g] = {"rows": len(idx), **{f: {"support": int(Yt[idx, k].sum()), "f1": round(prf(Yt[idx, k], rule_te[idx, k])["f1"], 2)} for k, f in enumerate(FLAGS5)}}
out["rules_by_group_historical_test"] = groups
json.dump(out, open(ROOT / "research" / "results" / "evaluation_all.json", "w"), indent=1)
print(f"{'flag':17} {'rules F1 [95% CI]':24} {'sparse model F1':16} {'selected (validation)':22} {'selected F1 [95% CI]':24} diff-vs-rules 95% CI")
for f, ru, pick, sel, sp in table:
    print(f"{f:17} {ru['f1']:.2f} [{ru['f1_ci95'][0]:.2f},{ru['f1_ci95'][1]:.2f}]      {sp['f1']:.2f}             {pick:22} {sel['f1']:.2f} [{sel['f1_ci95'][0]:.2f},{sel['f1_ci95'][1]:.2f}]      {sel['f1_minus_rules_ci95']}")
print("macro/micro F1 rules:", out["rules_macro_f1"], out["rules_micro_f1"], "| selected:", out["selected_macro_f1"], out["selected_micro_f1"])
