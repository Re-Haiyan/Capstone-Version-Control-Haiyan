"""Phase 4: fine-tune the XLM-R sentiment classifier on policy-v1 rows (Claude-labelled, recorded as Claude, not ChatGPT) with a fixed PRODUCT-GROUPED train/dev split. CPU only.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/finetune_v1.py --name p4_full_s1 --mode full --seed 1
    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/finetune_v1.py --name p4_top2_s1 --mode top2 --seed 1

Split: StratifiedGroupKFold(5, shuffle, random_state=11) over all three-class v1 rows (dev pool + 3,000 candidates), fold 0 = development validation (about 20% of the products), the other four folds = training.
The same fold is scored by the head experiments (phase4_experiments.py, split seed 11, fold 0) so the numbers are comparable. Epoch selection uses ONLY this development fold. The frozen test, the Phase 3
confirmation set and held-out v2 are never read. Modes: full (all layers; the word-embedding matrix stays frozen as in finetune.py), top2 (parameter-efficient variant: word embeddings and the lower 10 encoder
layers frozen, the top 2 layers + classification head trained). The `peft` package is not installed in this environment, so LoRA was not run. Checkpoints go to D:/defaketive-train/xlmr/<name>/best (outside the repository).
"""
import argparse, json, pathlib, random, sys, time
import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata, metrics_x, phase3_experiments as p3  # noqa: E402
from inference import CARDIFF  # noqa: E402
from sklearn.model_selection import StratifiedGroupKFold  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--mode", choices=("full", "top2"), default="full")
ap.add_argument("--lr", type=float, default=2e-5)
ap.add_argument("--epochs", type=int, default=3)
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--max-len", type=int, default=128)
ap.add_argument("--threads", type=int, default=12)
a = ap.parse_args()
random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed); torch.set_num_threads(a.threads)
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup  # noqa: E402

L = xdata.LABELS
rows = [r for r in p3.v1_rows() if r["label"] in L]
y_all = np.array([L.index(r["label"]) for r in rows]); g_all = np.array([r["group"] for r in rows])
tr_i, dv_i = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=11).split(np.zeros(len(rows)), y_all, g_all))[0]
assert not set(g_all[tr_i]) & set(g_all[dv_i])
train = [rows[i] for i in tr_i]; dev = [rows[i] for i in dv_i]
y_train = y_all[tr_i]; counts = np.bincount(y_train, minlength=3)
weights = torch.tensor(counts.sum() / (3 * counts), dtype=torch.float)
print(f"train rows {len(train)} {counts.tolist()} dev rows {len(dev)} {np.bincount(y_all[dv_i], minlength=3).tolist()} mode {a.mode} lr {a.lr} epochs {a.epochs} seed {a.seed}", flush=True)

tok = AutoTokenizer.from_pretrained(CARDIFF, local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(CARDIFF, local_files_only=True)
model.roberta.embeddings.word_embeddings.weight.requires_grad = False
if a.mode == "top2":
    for p in model.roberta.parameters():
        p.requires_grad = False
    for layer in model.roberta.encoder.layer[-2:]:
        for p in layer.parameters():
            p.requires_grad = True
params = [p for p in model.parameters() if p.requires_grad]
n_train_params = sum(p.numel() for p in params); n_all = sum(p.numel() for p in model.parameters())
print(f"trainable parameters {n_train_params:,} of {n_all:,}", flush=True)


def batches(rs, shuffle):
    idx = list(range(len(rs)))
    if shuffle:
        random.shuffle(idx); chunk = a.batch * 50
        idx = sum([sorted(idx[i:i + chunk], key=lambda j: len(rs[j]["text"])) for i in range(0, len(idx), chunk)], [])
        gs = [idx[i:i + a.batch] for i in range(0, len(idx), a.batch)]; random.shuffle(gs)
    else:
        idx = sorted(idx, key=lambda j: len(rs[j]["text"])); gs = [idx[i:i + 64] for i in range(0, len(idx), 64)]
    return gs


def encode(rs, g):
    return tok([rs[j]["text"] for j in g], padding=True, truncation=True, max_length=a.max_len, return_tensors="pt")


def predict(rs):
    model.eval(); out = np.zeros((len(rs), 3))
    with torch.no_grad():
        for g in batches(rs, False):
            out[g] = torch.softmax(model(**encode(rs, g)).logits.float(), -1).numpy()
    return out


def score(rs, prob):
    yy = np.array([L.index(r["label"]) for r in rs]); s = metrics_x.summarize(yy, prob.argmax(1)); c = s["classes"]
    nat = np.array([r["set"] == "dev_pool" for r in rs])
    sn = metrics_x.summarize(yy[nat], prob.argmax(1)[nat])
    return {"macro_f1": s["macro_f1"], "accuracy": s["accuracy"], "weighted_f1": s["weighted_f1"], "macro_precision": float(np.mean([c[k]["precision"] for k in L])), "macro_recall": float(np.mean([c[k]["recall"] for k in L])),
            "f1": {k: c[k]["f1"] for k in L}, "precision": {k: c[k]["precision"] for k in L}, "recall": {k: c[k]["recall"] for k in L}, "confusion": s["confusion"],
            "natural_distribution_dev_pool": {"n": int(nat.sum()), "macro_f1": sn["macro_f1"], "neutral_f1": sn["classes"]["neutral"]["f1"], "confusion": sn["confusion"]}}


opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.01)
total = ((len(train) + a.batch - 1) // a.batch) * a.epochs
sched = get_linear_schedule_with_warmup(opt, int(total * 0.06), total)
lossf = torch.nn.CrossEntropyLoss(weight=weights)
out_dir = pathlib.Path("D:/defaketive-train/xlmr") / a.name; out_dir.mkdir(parents=True, exist_ok=True)
history, best, step, t0 = [], -1.0, 0, time.time()
base = score(dev, predict(dev)); print("before training (public checkpoint, dev fold): macroF1", round(base["macro_f1"], 4), flush=True)
best_prob = None
for epoch in range(1, a.epochs + 1):
    model.train(); run = 0.0
    for g in batches(train, True):
        enc = encode(train, g); yb = torch.tensor([L.index(train[j]["label"]) for j in g])
        loss = lossf(model(**enc).logits, yb); loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step(); sched.step(); opt.zero_grad()
        step += 1; run += loss.item()
        if step % 50 == 0:
            print(f"epoch {epoch} step {step}/{total} loss {run / 50:.4f} elapsed {time.time() - t0:.0f}s", flush=True); run = 0.0
    prob = predict(dev); ev = score(dev, prob); ev["epoch"] = epoch; ev["seconds"] = round(time.time() - t0); history.append(ev)
    print(f"epoch {epoch}: dev macroF1 {ev['macro_f1']:.4f} acc {ev['accuracy']:.3f} F1 neg/neu/pos {ev['f1']['negative']:.2f}/{ev['f1']['neutral']:.2f}/{ev['f1']['positive']:.2f} natural-dist mF1 {ev['natural_distribution_dev_pool']['macro_f1']:.3f}", flush=True)
    if ev["macro_f1"] > best:
        best = ev["macro_f1"]; best_prob = prob; model.save_pretrained(out_dir / "best"); tok.save_pretrained(out_dir / "best")
sel = max(history, key=lambda h: h["macro_f1"])
json.dump({"args": vars(a), "annotator": "Claude (policy v1), not ChatGPT", "train_rows": len(train), "dev_rows": len(dev), "trainable_parameters": n_train_params, "all_parameters": n_all, "before_training_dev": base, "history": history,
           "selected_epoch_on_dev_fold": sel["epoch"], "selected": sel, "seconds_total": round(time.time() - t0), "torch": torch.__version__, "threads": a.threads,
           "dev_ids": [r["id"] for r in dev], "dev_probabilities_selected_epoch": best_prob.round(4).tolist()}, open(xdata.X / "runs" / f"{a.name}.json", "w"))
print("done", round(time.time() - t0), "s; best dev macro F1", round(best, 4))
