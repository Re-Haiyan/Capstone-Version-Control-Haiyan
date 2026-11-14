"""Fine-tune the review-flag model: one XLM-RoBERTa, five yes/no outputs (defect, counterfeit, safety,
not_as_described, quality), reading the product category, the product title and the whole review.

Run it with the training environment (not the app's), from the repository folder:

    D:\\defaketive-train\\Scripts\\python.exe training\\train_label_model.py --time-only
    D:\\defaketive-train\\Scripts\\python.exe training\\train_label_model.py ^
        --train evaluation\\annotated\\train_part1.csv ... --test evaluation\\annotated\\test_set.csv --out training\\runs\\v1

Files are the labelled batches: id, stars, product, review_text, sentiment, flags, confidence. Only rows with
confidence=high are used. The key file beside each batch (same name + _key.csv) gives the product category.
A test file is never trained on, and nothing is tuned on it: thresholds are chosen on a validation slice that is
cut from the training rows BY PRODUCT (reviews of one product look alike, so a split by review would flatter the score).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import random
import sys
import time

import numpy as np
import torch
from sklearn.metrics import precision_recall_fscore_support
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

BASE_FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality")
FLAGS = BASE_FLAGS  # set in main(): BASE_FLAGS + ("delivery",) with --with-delivery
BASE = "cardiffnlp/twitter-xlm-roberta-base-sentiment"  # the checkpoint the app's sentiment model was built from
ROOT = pathlib.Path(__file__).resolve().parent.parent


def read_batch(path: pathlib.Path) -> list[dict]:
    key_path = path.with_name(path.stem + "_key.csv")
    key = {}
    if key_path.is_file():
        key = {r["id"]: r for r in csv.DictReader(open(key_path, encoding="utf-8-sig"))}
    rows = []
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        if (r.get("confidence") or "").strip().lower() != "high" or not (r.get("flags") or "").strip():
            continue
        gold = {f for f in r["flags"].replace(" ", "").split(";") if f in FLAGS}
        category = (key.get(r["id"]) or {}).get("category", "")
        rows.append({"id": r["id"], "product": " ".join(r["product"].split()), "stars": r["stars"], "text": r["review_text"],
                     "category": category, "y": [1.0 if f in gold else 0.0 for f in FLAGS]})
    return rows


def model_text(row: dict) -> str:
    """The category and title come first, so the model reads the review knowing what product it is about."""
    kind = row["category"].replace("_", " ") if row["category"] else "product"
    return f"{kind} | {row['product'][:120]} | {row['stars']} stars </s> {row['text']}"


def by_product(rows: list[dict], percent: int, salt: str):
    hold = [r for r in rows if int(hashlib.md5((salt + r["product"]).encode()).hexdigest(), 16) % 100 < percent]
    names = {id(r) for r in hold}
    return [r for r in rows if id(r) not in names], hold


def batches(rows, size, tokenizer, max_len, shuffle):
    order = list(range(len(rows)))
    if shuffle:
        # Similar lengths share a batch (less padding, so faster); the batches themselves come in random order.
        random.shuffle(order)
        chunks = [sorted(order[i:i + size * 50], key=lambda j: len(rows[j]["text"])) for i in range(0, len(order), size * 50)]
        grouped = [c[i:i + size] for c in chunks for i in range(0, len(c), size)]
        random.shuffle(grouped)
        order = [j for g in grouped for j in g]
    else:  # evaluation: group by length, it is faster and does not change a score
        order.sort(key=lambda i: len(rows[i]["text"]))
    for start in range(0, len(order), size):
        part = [rows[i] for i in order[start:start + size]]
        enc = tokenizer([model_text(r) for r in part], truncation=True, max_length=max_len, padding=True, return_tensors="pt")
        yield [order[start + k] for k in range(len(part))], enc, torch.tensor([r["y"] for r in part], dtype=torch.float32)


@torch.no_grad()
def predict(model, rows, tokenizer, max_len):
    model.eval()
    out = np.zeros((len(rows), len(FLAGS)), dtype=np.float32)
    for idx, enc, _ in batches(rows, 32, tokenizer, max_len, False):
        out[idx] = torch.sigmoid(model(**enc).logits).numpy()
    return out


def scores(y, p, thresholds):
    table = {}
    for k, name in enumerate(FLAGS):
        pred = p[:, k] >= thresholds[k]
        prec, rec, f1, _ = precision_recall_fscore_support(y[:, k], pred, average="binary", zero_division=0)
        table[name] = {"positives": int(y[:, k].sum()), "precision": round(float(prec), 3), "recall": round(float(rec), 3), "f1": round(float(f1), 3)}
    return table


def best_thresholds(y, p):
    result = []
    for k in range(len(FLAGS)):
        best, best_f1 = 0.5, -1.0
        for t in np.arange(0.1, 0.91, 0.05):
            pred = p[:, k] >= t
            tp = float(((pred == 1) & (y[:, k] == 1)).sum()); fp = float(((pred == 1) & (y[:, k] == 0)).sum()); fn = float(((pred == 0) & (y[:, k] == 1)).sum())
            f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
            if f1 > best_f1:
                best, best_f1 = float(t), f1
        result.append(round(best, 2))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", nargs="*", default=[])
    ap.add_argument("--test", nargs="*", default=[])
    ap.add_argument("--out", default=str(ROOT / "training" / "runs" / "v1"))
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-len", type=int, default=160)
    ap.add_argument("--threads", type=int, default=12)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--train-embeddings", action="store_true", help="also train the 250,000-word embedding table (slower, rarely better)")
    ap.add_argument("--with-delivery", action="store_true", help="add a sixth output: a complaint about delivery, packaging or the seller")
    ap.add_argument("--time-only", action="store_true", help="run a few steps on made-up rows and report seconds per step")
    args = ap.parse_args()

    global FLAGS
    FLAGS = BASE_FLAGS + (("delivery",) if args.with_delivery else ())
    torch.set_num_threads(args.threads)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSequenceClassification.from_pretrained(BASE, num_labels=len(FLAGS), problem_type="multi_label_classification", ignore_mismatched_sizes=True)

    if not args.train_embeddings:
        for parameter in model.roberta.embeddings.word_embeddings.parameters():
            parameter.requires_grad = False
    trainable = [q for q in model.parameters() if q.requires_grad]

    if args.time_only:
        rows = [{"product": "Rice cooker 1.8L", "stars": "2", "category": "small_appliance", "y": [1.0, 0.0, 0.0, 0.0, 1.0] + [0.0] * (len(FLAGS) - 5),
                 "text": "Hindi gumana ang switch at manipis ang takip, nadismaya ako sa binili ko " * 2}] * 64
        opt = torch.optim.AdamW(trainable, lr=args.lr)
        model.train(); steps = 0; start = time.time()
        for _, enc, y in batches(rows, args.batch, tokenizer, args.max_len, True):
            loss = torch.nn.functional.binary_cross_entropy_with_logits(model(**enc).logits, y)
            loss.backward(); opt.step(); opt.zero_grad(); steps += 1
            print(f"step {steps}: {time.time() - start:.1f}s total", flush=True)
            if steps == 4:
                break
        per_step = (time.time() - start) / steps
        print(f"{per_step:.2f} s per step of {args.batch}; 3,000 rows x {args.epochs} epochs = about {3000 / args.batch * args.epochs * per_step / 60:.0f} minutes")
        return

    train_rows = [r for f in args.train for r in read_batch(pathlib.Path(f))]
    test_rows = [r for f in args.test for r in read_batch(pathlib.Path(f))]
    train_rows, valid_rows = by_product(train_rows, 12, "valid")
    if not train_rows or not test_rows:
        sys.exit("Give --train and --test files that hold labelled, high-confidence rows.")
    y_train = np.array([r["y"] for r in train_rows])
    print(f"train {len(train_rows)}  validation {len(valid_rows)}  test {len(test_rows)}")
    print("train positives:", dict(zip(FLAGS, y_train.sum(0).astype(int))))
    pos = y_train.sum(0); neg = len(y_train) - pos
    weight = torch.tensor(np.clip(neg / np.maximum(pos, 1), 1.0, 6.0), dtype=torch.float32)  # the rare labels count for more

    opt = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.01)
    total = math.ceil(len(train_rows) / args.batch) * args.epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * total), total)
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    best_macro, best_state, history = -1.0, None, []
    start = time.time()
    for epoch in range(1, args.epochs + 1):
        model.train(); running = 0.0; n = 0
        for _, enc, y in batches(train_rows, args.batch, tokenizer, args.max_len, True):
            loss = torch.nn.functional.binary_cross_entropy_with_logits(model(**enc).logits, y, pos_weight=weight)
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad(); running += loss.item(); n += 1
        p_valid = predict(model, valid_rows, tokenizer, args.max_len)
        y_valid = np.array([r["y"] for r in valid_rows])
        thr = best_thresholds(y_valid, p_valid)
        s = scores(y_valid, p_valid, thr)
        macro = float(np.mean([s[f]["f1"] for f in FLAGS if s[f]["positives"] >= 3] or [0]))
        history.append({"epoch": epoch, "loss": round(running / n, 4), "validation_macro_f1": round(macro, 3), "minutes": round((time.time() - start) / 60, 1)})
        print(history[-1], flush=True)
        if macro > best_macro:
            best_macro = macro; best_thr = thr
            model.save_pretrained(out / "model"); tokenizer.save_pretrained(out / "model")

    model = AutoModelForSequenceClassification.from_pretrained(out / "model")
    p_test = predict(model, test_rows, tokenizer, args.max_len)
    y_test = np.array([r["y"] for r in test_rows])
    result = {"thresholds_chosen_on_validation": dict(zip(FLAGS, best_thr)), "history": history, "test_rows": len(test_rows),
              "test": scores(y_test, p_test, best_thr)}
    json.dump(result, open(out / "metrics.json", "w", encoding="utf-8"), indent=2)
    np.save(out / "test_probabilities.npy", p_test)
    json.dump([r["id"] for r in test_rows], open(out / "test_ids.json", "w"))
    print(json.dumps(result["test"], indent=2))


if __name__ == "__main__":
    main()
