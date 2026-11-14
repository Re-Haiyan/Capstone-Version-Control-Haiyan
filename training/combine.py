"""Pick, per label, how to combine the rules and the model on the VALIDATION rows, then report the test rows."""
import json, sys
FL = ("defect", "counterfeit", "safety", "not_as_described", "quality", "delivery")
run = sys.argv[1] + "/"
pr = json.load(open(run + "probs.json")); ru = json.load(open(run + "rules.json")); thr = json.load(open(run + "metrics.json"))["thresholds_chosen_on_validation"]
FL = tuple(f for f in FL if f in thr)
for _id, _flags in ru.items():
    ru[_id] = list(_flags) + [0] * (len(FL) - len(_flags))
def f1(y, p):
    tp = sum(1 for a, b in zip(y, p) if a and b); fp = sum(1 for a, b in zip(y, p) if not a and b); fn = sum(1 for a, b in zip(y, p) if a and not b)
    P = tp / (tp + fp) if tp + fp else 0; R = tp / (tp + fn) if tp + fn else 0
    return (2 * P * R / (P + R) if P + R else 0), P, R
def strategies(t, lo):
    return {"rules": lambda r, p: r, "model": lambda r, p: p >= t, "OR": lambda r, p: r or p >= t, "AND": lambda r, p: r and p >= t,
            "rules_veto_lo": lambda r, p: r and p >= lo, "model_or_rules_hi": lambda r, p: (p >= t) or (r and p >= lo)}
chosen = {}
for k, name in enumerate(FL):
    t = thr[name]; best = None
    for lo in (0.02, 0.05, 0.1, 0.2, 0.3):
        for sn, fn in strategies(t, lo).items():
            yv = [x["y"][k] for x in pr["valid"]]; pv = [bool(fn(ru[x["id"]][k], x["p"][k])) for x in pr["valid"]]
            s = f1(yv, pv)[0]
            if best is None or s > best[0]: best = (s, sn, lo)
    rules_val = f1([x["y"][k] for x in pr["valid"]], [bool(ru[x["id"]][k]) for x in pr["valid"]])[0]
    if best[0] < rules_val + 0.03:  # a model only joins the rules if it clearly helps on validation
        best = (rules_val, "rules", 0.02)
    s, sn, lo = best; fn = strategies(t, lo)[sn]; chosen[name] = {"strategy": sn, "lo": lo, "t": t}
    yt = [x["y"][k] for x in pr["test"]]
    mt = f1(yt, [bool(fn(ru[x["id"]][k], x["p"][k])) for x in pr["test"]])
    rt = f1(yt, [bool(ru[x["id"]][k]) for x in pr["test"]]); mo = f1(yt, [x["p"][k] >= t for x in pr["test"]])
    print(f"{name:17} val_pos={sum(x['y'][k] for x in pr['valid']):3} chose {sn:18} lo={lo:<4} | test F1 rules {rt[0]:.2f}  model {mo[0]:.2f}  combo {mt[0]:.2f} (P {mt[1]:.2f} R {mt[2]:.2f})")
json.dump(chosen, open(run + "combination.json", "w"), indent=1)
