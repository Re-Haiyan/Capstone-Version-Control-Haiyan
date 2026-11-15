"""Fine-tune the XLM-R sentiment classifier (CPU) on FiReCS and/or team-labelled marketplace reviews, with validation-based selection.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/finetune.py --name b_firecs_s1 --mix firecs --seed 1

Never reads market_test_v3 or FiReCS test. Selection metric: macro F1 on the marketplace VALIDATION split (36 held-out products of
train_v3; team-supplied labels, unverified), with the FiReCS validation macro F1 recorded alongside. The best epoch is kept.
--loss: ce | weighted (class weights, inverse frequency of the training mixture) | balanced (class-balanced sampling).
Checkpoints go to D:/defaketive-train/xlmr/<name>/best (outside the repository); metrics to research/xlmr_optimization/runs/<name>.json.
"""
import argparse, json, pathlib, random, sys, time
import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata, metrics_x  # noqa: E402
from inference import CARDIFF  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--mix", choices=("firecs", "firecs+market", "market"), default="firecs")
ap.add_argument("--init", default=CARDIFF, help="checkpoint to continue from (default: the public base checkpoint)")
ap.add_argument("--loss", choices=("ce", "weighted", "balanced"), default="ce")
ap.add_argument("--lr", type=float, default=2e-5)
ap.add_argument("--epochs", type=int, default=3)
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--wd", type=float, default=0.01)
ap.add_argument("--warmup", type=float, default=0.06)
ap.add_argument("--max-len", type=int, default=128)
ap.add_argument("--dropout", type=float, default=None)
ap.add_argument("--no-freeze-emb", action="store_true")
ap.add_argument("--max-steps", type=int, default=0)
ap.add_argument("--market-repeat", type=int, default=1, help="times the marketplace rows are repeated per epoch in a mixture")
a = ap.parse_args()

random.seed(a.seed)
np.random.seed(a.seed)
torch.manual_seed(a.seed)
torch.set_num_threads(12)
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup  # noqa: E402

local = a.init == CARDIFF
tok = AutoTokenizer.from_pretrained(a.init, local_files_only=local)
kw = {"hidden_dropout_prob": a.dropout} if a.dropout is not None else {}
model = AutoModelForSequenceClassification.from_pretrained(a.init, local_files_only=local, **kw)
if not a.no_freeze_emb:
    model.roberta.embeddings.word_embeddings.weight.requires_grad = False

splits = json.load(open(xdata.DATA / "splits.json"))
fc = {r["id"]: r for r in xdata.load_firecs("train")}
mk = {r["id"]: r for r in xdata.load_marketplace()["market_train_v3"]}


def pick(ids, table):
    return [table[i] for i in ids]


train = []
if "firecs" in a.mix:
    train += pick(splits["firecs_train"], fc)
if "market" in a.mix:
    train += pick(splits["market_train"], mk) * a.market_repeat
val_f, val_m = pick(splits["firecs_val"], fc), pick(splits["market_val"], mk)
y_train = np.array([xdata.LABELS.index(r["label"]) for r in train])
counts = np.bincount(y_train, minlength=3)
weights = torch.tensor(counts.sum() / (3 * counts), dtype=torch.float) if a.loss == "weighted" else None
print(f"train rows {len(train)} class counts {counts.tolist()} loss {a.loss} lr {a.lr} epochs {a.epochs} seed {a.seed}", flush=True)


def batches(rows, y, shuffle):
    idx = list(range(len(rows)))
    if shuffle:
        if a.loss == "balanced":
            p = (1.0 / counts)[y]
            p = p / p.sum()
            idx = list(np.random.choice(len(rows), len(rows), p=p))
        else:
            random.shuffle(idx)
        chunk = a.batch * 50  # length-grouped batches inside random chunks: far less padding
        idx = sum([sorted(idx[i:i + chunk], key=lambda j: len(rows[j]["text"])) for i in range(0, len(idx), chunk)], [])
        groups = [idx[i:i + a.batch] for i in range(0, len(idx), a.batch)]
        random.shuffle(groups)
    else:
        idx = sorted(idx, key=lambda j: len(rows[j]["text"]))
        groups = [idx[i:i + 64] for i in range(0, len(idx), 64)]
    return groups


def encode(rows, g):
    return tok([rows[j]["text"] for j in g], padding=True, truncation=True, max_length=a.max_len, return_tensors="pt")


def evaluate(rows):
    y = np.array([xdata.LABELS.index(r["label"]) for r in rows])
    model.eval()
    out = np.zeros((len(rows), 3))
    with torch.no_grad():
        for g in batches(rows, y, False):
            out[g] = torch.softmax(model(**encode(rows, g)).logits.float(), -1).numpy()
    s = metrics_x.summarize(y, out.argmax(1))
    c = s["classes"]
    return {"macro_f1": s["macro_f1"], "accuracy": s["accuracy"], "negative_recall": c["negative"]["recall"], "neutral_f1": c["neutral"]["f1"],
            "negative_f1": c["negative"]["f1"], "positive_f1": c["positive"]["f1"]}


params = [p for p in model.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=a.wd)
steps_per_epoch = (len(train) + a.batch - 1) // a.batch
total = a.max_steps if a.max_steps else steps_per_epoch * a.epochs
sched = get_linear_schedule_with_warmup(opt, int(total * a.warmup), total)
lossf = torch.nn.CrossEntropyLoss(weight=weights)
out_dir = pathlib.Path("D:/defaketive-train/xlmr") / a.name
out_dir.mkdir(parents=True, exist_ok=True)
history, best, step, t0 = [], -1.0, 0, time.time()
base_eval = {"firecs_val": evaluate(val_f), "market_val": evaluate(val_m)}
print("before training:", {k: round(v["macro_f1"], 4) for k, v in base_eval.items()}, flush=True)
for epoch in range(1, a.epochs + 1):
    model.train()
    run = 0.0
    for g in batches(train, y_train, True):
        enc = encode(train, g)
        y = torch.tensor([xdata.LABELS.index(train[j]["label"]) for j in g])
        loss = lossf(model(**enc).logits, y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        sched.step()
        opt.zero_grad()
        step += 1
        run += loss.item()
        if step % 50 == 0:
            print(f"epoch {epoch} step {step}/{total} loss {run / 50:.4f} elapsed {time.time() - t0:.0f}s", flush=True)
            run = 0.0
        if a.max_steps and step >= a.max_steps:
            break
    ev = {"epoch": epoch, "firecs_val": evaluate(val_f), "market_val": evaluate(val_m), "seconds": round(time.time() - t0)}
    history.append(ev)
    sel = ev["market_val"]["macro_f1"]
    print(f"epoch {epoch}: market_val macroF1 {sel:.4f} (neu {ev['market_val']['neutral_f1']:.3f}, neg recall {ev['market_val']['negative_recall']:.3f}) firecs_val macroF1 {ev['firecs_val']['macro_f1']:.4f}", flush=True)
    if sel > best:
        best = sel
        model.save_pretrained(out_dir / "best")
        tok.save_pretrained(out_dir / "best")
    if a.max_steps and step >= a.max_steps:
        break
json.dump({"args": vars(a), "train_rows": len(train), "class_counts": counts.tolist(), "before_training": base_eval, "history": history,
           "selected_epoch": max(history, key=lambda h: h["market_val"]["macro_f1"])["epoch"], "torch": torch.__version__, "seconds": round(time.time() - t0)},
          open(xdata.X / "runs" / f"{a.name}.json", "w"), indent=1)
print("done", round(time.time() - t0), "s; best market_val macro F1", round(best, 4))
