"""Table of every fine-tuning run: arguments, rows, per-epoch validation results, time (reads runs/*.json)."""
import glob, json, pathlib
X = pathlib.Path(__file__).resolve().parent
print("| Run | mix / loss / lr / epochs / seed | rows | before: market val, FiReCS val (macro F1) | epoch results: market val macro F1 (neutral F1, neg recall) / FiReCS val | selected epoch | minutes |")
print("|---|---|---:|---|---|---:|---:|")
for f in sorted(glob.glob(str(X / "runs" / "*.json"))):
    d = json.load(open(f)); a = d["args"]; b = d["before_training"]
    ep = "; ".join(f"e{h['epoch']}: {h['market_val']['macro_f1']:.3f} ({h['market_val']['neutral_f1']:.2f}, {h['market_val']['negative_recall']:.2f}) / {h['firecs_val']['macro_f1']:.3f}" for h in d["history"])
    extra = f", repeat {a['market_repeat']}" if a.get("market_repeat", 1) != 1 else ""
    print(f"| {a['name']} | {a['mix']} / {a['loss']} / {a['lr']:g} / {a['epochs']} / {a['seed']}{extra} | {d['train_rows']} | {b['market_val']['macro_f1']:.3f}, {b['firecs_val']['macro_f1']:.3f} | {ep} | {d['selected_epoch']} | {d['seconds'] / 60:.0f} |")
