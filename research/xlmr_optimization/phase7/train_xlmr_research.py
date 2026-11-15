"""Research-only XLM-RoBERTa last-two-layer sentiment fine-tuning.

Uses ONLY the frozen Claude-v1 3,400-row *development* sheets already in this
repository. These are AI-assisted labels, NOT human-validated gold data.
Never reads frozen final tests, confirmation labels, production database, or VM.

Audit only (no model download):
  python research/xlmr_optimization/phase7/train_xlmr_research.py --audit-only --output /tmp/xlmr-p7

Training:
  python research/xlmr_optimization/phase7/train_xlmr_research.py --output /tmp/xlmr-p7 --epochs 2

Requires Python 3.11, numpy, scikit-learn, torch, transformers, safetensors.
Model is trained on review text ONLY. Titles are grouping proxies, not features.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import os
import pathlib
import random
import re
import subprocess
import unicodedata

BASE = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
LABELS = ("negative", "neutral", "positive")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
ANN = ROOT / "annotation"
SOURCES = (
    ("dev", "dev_pool_sheet.csv", "dev_pool_sheet_ai_v1.csv", 400),
    ("candidates", "neutral_candidate_pool.csv", "neutral_candidate_pool_ai_v1.csv", 3000),
)
UNCHANGED_FIELDS = ("id", "product", "category_group", "platform", "language_hint", "review_text")


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or not all("id" in row for row in rows):
        raise ValueError("Invalid or empty annotation sheet: " + path.name)
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate review IDs in " + path.name)
    return rows


def group_key(text):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", text or "").casefold()))


def text_key(text):
    return group_key(text)


def load_verified_development():
    rows, provenance = [], {}
    used_ids = set()
    for scope, src_file, ai_file, count in SOURCES:
        original_path = ANN / src_file
        labelled_path = ANN / "ai_labelled" / ai_file
        original = read_csv(original_path)
        labelled = read_csv(labelled_path)
        if len(original) != count or len(labelled) != count:
            raise ValueError("Source counts differ from frozen protocol for " + scope)
        source = {r["id"]: r for r in original}
        if set(source) != {r["id"] for r in labelled}:
            raise ValueError("Source IDs differ from frozen protocol for " + scope)
        provenance[scope] = {
            "original_sha256": file_hash(original_path),
            "ai_label_sha256": file_hash(labelled_path),
            "input_rows": count,
        }
        for row in labelled:
            rid = row["id"]
            if rid in used_ids:
                raise ValueError("Cross-file repeated ID: " + rid)
            used_ids.add(rid)
            if any(row.get(f, "") != source[rid].get(f, "") for f in UNCHANGED_FIELDS):
                raise ValueError("Source customer review metadata or text was modified: " + rid)
            label = row.get("sentiment", "").strip().lower()
            conf = row.get("confidence", "").strip().lower()
            if label not in (*LABELS, "mixed", "unclear") or conf not in ("high", "low"):
                raise ValueError("Invalid Claude annotation: " + rid)
            rows.append({
                "id": rid, "scope": scope, "text": row["review_text"],
                "label": label, "confidence": conf, "group": group_key(row["product"]),
                "language": row["language_hint"].strip().lower(),
                "no_opinion": "no-opinion" in row.get("tags", "").lower().split(";"),
            })
    return rows, provenance


def split_development(rows, seed):
    """Development-only validation: grouped by normalized title (NOT verified product IDs).

    Only DEV-POOL rows can validate, so Neutral-candidate oversampling does not
    dominate the selection score. All matching-title candidates are excluded
    from training, and exact text overlaps are deleted from training.
    """
    from sklearn.model_selection import StratifiedGroupKFold

    filtered = [r for r in rows
                if r["label"] in LABELS and r["confidence"] == "high" and r["group"]
                and r["text"].strip()]
    dev = [r for r in filtered if r["scope"] == "dev"]
    if len(dev) < 250:
        raise RuntimeError("Too few high-confidence natural development reviews")
    skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    indices = list(skf.split([r["text"] for r in dev],
                             [LABELS.index(r["label"]) for r in dev],
                             [r["group"] for r in dev]))
    _, held = indices[0]
    valid = [dev[int(i)] for i in held]
    valid_groups = {r["group"] for r in valid}
    train = [r for r in filtered if r["group"] not in valid_groups]
    # Never train on an identical review appearing under a different title.
    val_keys = {text_key(r["text"]) for r in valid}
    train = [r for r in train if text_key(r["text"]) not in val_keys]

    # Remove conflicting Claude labels for identical text; deduplicate the rest.
    groups = collections.defaultdict(list)
    for r in train:
        groups[text_key(r["text"])].append(r)
    train = [rlist[0] for rlist in groups.values()
             if len({r["label"] for r in rlist}) == 1]
    # Deduplicate validation without resolving its labels using training data.
    val_by_text = collections.defaultdict(list)
    for r in valid:
        val_by_text[text_key(r["text"])].append(r)
    valid = [rlist[0] for rlist in val_by_text.values()
             if len({r["label"] for r in rlist}) == 1]
    if set(r["group"] for r in train) & set(r["group"] for r in valid):
        raise AssertionError("Title-group leakage")
    if set(text_key(r["text"]) for r in train) & set(text_key(r["text"]) for r in valid):
        raise AssertionError("Exact review-text leakage")
    t_counts = collections.Counter(r["label"] for r in train)
    v_counts = collections.Counter(r["label"] for r in valid)
    if len(train) < 1500 or len(valid) < 35 or min(v_counts.get(c, 0) for c in LABELS) < 3:
        raise RuntimeError("Insufficient valid three-class train/validation support")
    report = {
        "all_source_rows": len(rows),
        "eligible_high_confidence_with_title": len(filtered),
        "training_rows": len(train),
        "validation_rows": len(valid),
        "train_label_counts": dict(t_counts),
        "validation_label_counts": dict(v_counts),
        "training_title_groups": len({r["group"] for r in train}),
        "validation_title_groups": len({r["group"] for r in valid}),
        "validation_languages": dict(collections.Counter(r["language"] for r in valid)),
        "validation_no_opinion_rows": sum(r["no_opinion"] for r in valid),
        "grouping_limit": "normalized product title proxy; authentic marketplace product IDs unavailable",
        "near_duplicate_limit": "exact normalized text excluded; semantic near-duplicates not proven absent",
    }
    return train, valid, report


def score(y, pred):
    import numpy as np
    from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
    p, r, f, support = precision_recall_fscore_support(
        y, pred, labels=[0, 1, 2], zero_division=0)
    return {
        "n": len(y), "accuracy": round(float(accuracy_score(y, pred)), 4),
        "macro_f1": round(float(np.mean(f)), 4),
        "macro_precision": round(float(np.mean(p)), 4),
        "macro_recall": round(float(np.mean(r)), 4),
        "classes": {name: {
            "precision": round(float(p[k]), 4), "recall": round(float(r[k]), 4),
            "f1": round(float(f[k]), 4), "support": int(support[k])
        } for k, name in enumerate(LABELS)},
        "confusion_gold_rows_pred_columns": confusion_matrix(
            y, pred, labels=[0, 1, 2]).tolist(),
    }


def evaluate(model, tokenizer, rows, device, max_len):
    import torch
    model.eval()
    guesses = []
    with torch.inference_mode():
        for j in range(0, len(rows), 24):
            text = [r["text"] for r in rows[j:j + 24]]
            encoded = tokenizer(text, padding=True, truncation=True,
                                max_length=max_len, return_tensors="pt")
            logits = model(**{k: v.to(device) for k, v in encoded.items()}).logits
            guesses.extend(logits.argmax(-1).cpu().tolist())
    y = [LABELS.index(r["label"]) for r in rows]
    subsets = {
        "natural_dev": list(range(len(rows))),
        "non_no_opinion": [i for i, r in enumerate(rows) if not r["no_opinion"]],
        "filipino_taglish": [i for i, r in enumerate(rows)
                             if r["language"] in ("filipino", "taglish")],
        "delivery_or_other": [],  # intentionally not evaluated; no robust review-type field
    }
    result = {}
    for label, idx in subsets.items():
        if label == "delivery_or_other" or len(idx) < 15:
            continue
        result[label] = score([y[i] for i in idx], [guesses[i] for i in idx])
    return result


def train(args, train_rows, valid_rows, report, provenance):
    import numpy as np
    import torch
    from safetensors.torch import save_file
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from transformers import get_linear_schedule_with_warmup

    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    torch.set_num_threads(min(4, os.cpu_count() or 2))
    tokenizer = AutoTokenizer.from_pretrained(BASE, trust_remote_code=False, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, trust_remote_code=False)
    label_map = [str(model.config.id2label[i]).lower() for i in range(3)]
    if label_map != list(LABELS):
        raise RuntimeError("Pretrained output label order does not match: " + repr(label_map))

    # Pretrained encoder stays intact except final two encoder blocks + classifier.
    for param in model.parameters():
        param.requires_grad = False
    for layer in model.roberta.encoder.layer[-2:]:
        for param in layer.parameters():
            param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True
    params = [param for param in model.parameters() if param.requires_grad]
    trainable_names = {name for name, param in model.named_parameters()
                       if param.requires_grad}
    report["trainable_parameters"] = sum(x.numel() for x in params)
    report["base_model"] = BASE
    report["base_revision"] = getattr(model.config, "_commit_hash", None)
    report["tuning"] = "last-two XLM-R encoder layers and sequence classifier; earlier layers frozen"

    device = torch.device("cpu")
    model.to(device)
    before = evaluate(model, tokenizer, valid_rows, device, args.max_len)
    print("Cardiff baseline natural-dev macro F1:", before["natural_dev"]["macro_f1"], flush=True)

    counts = collections.Counter(LABELS.index(r["label"]) for r in train_rows)
    frequencies = np.array([counts[i] for i in range(3)], dtype=float)
    class_weights = (frequencies.sum() / (3 * frequencies)) ** 0.5
    class_weights = np.clip(class_weights, 0.5, 2.5)
    weights = torch.tensor(class_weights, dtype=torch.float32)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.01)
    optimizer_steps_per_epoch = math.ceil(math.ceil(len(train_rows) / args.batch) / args.grad_accum)
    total_steps = max(1, optimizer_steps_per_epoch * args.epochs)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(total_steps * 0.06), total_steps)
    history, best_f1, best_result = [], -1.0, None

    for epoch in range(args.epochs):
        model.train()
        indices = list(range(len(train_rows)))
        random.shuffle(indices)
        optimizer.zero_grad(set_to_none=True)
        loss_total, batches = 0.0, 0
        for start in range(0, len(indices), args.batch):
            idx = indices[start:start + args.batch]
            encoded = tokenizer([train_rows[i]["text"] for i in idx],
                                padding=True, truncation=True,
                                max_length=args.max_len, return_tensors="pt")
            target = torch.tensor([LABELS.index(train_rows[i]["label"]) for i in idx])
            loss = loss_fn(model(**encoded).logits, target)
            (loss / args.grad_accum).backward()
            loss_total += float(loss.detach()); batches += 1
            if batches % args.grad_accum == 0 or start + args.batch >= len(indices):
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                optimizer.step(); scheduler.step()
                optimizer.zero_grad(set_to_none=True)
        result = evaluate(model, tokenizer, valid_rows, device, args.max_len)
        entry = {
            "epoch": epoch + 1, "mean_training_loss": round(loss_total / batches, 5),
            "validation": result,
        }
        history.append(entry)
        f1 = result["natural_dev"]["macro_f1"]
        print("epoch", epoch + 1, "natural-dev macro F1", f1,
              "neutral F1", result["natural_dev"]["classes"]["neutral"]["f1"], flush=True)
        if f1 > best_f1:
            best_f1, best_result = f1, entry
            tensors = {name: param.detach().cpu().contiguous()
                       for name, param in model.named_parameters()
                       if name in trainable_names}
            save_file(tensors, str(args.output / "adapter_delta.safetensors"))

    base_n = before["natural_dev"]
    best_n = best_result["validation"]["natural_dev"]
    language_before = before.get("filipino_taglish", {}).get("macro_f1")
    language_after = best_result["validation"].get("filipino_taglish", {}).get("macro_f1")
    gates = {
        "natural_dev_macro_f1_improves": best_n["macro_f1"] > base_n["macro_f1"],
        "natural_dev_neutral_f1_non_decreasing":
            best_n["classes"]["neutral"]["f1"] >= base_n["classes"]["neutral"]["f1"],
        "natural_dev_negative_recall_drop_at_most_0_05":
            best_n["classes"]["negative"]["recall"] >= base_n["classes"]["negative"]["recall"] - 0.05,
        "filipino_taglish_macro_f1_drop_at_most_0_05":
            language_before is None or language_after is None
            or language_after >= language_before - 0.05,
        "independent_marketplace_test": False,
        "human_adjudicated_reference": False,
        "product_conclusion_validation": False,
    }
    results = {
        "status": "research_only_not_approved_for_vm_or_production",
        "provenance": "Claude-v1 AI-assisted sentiment labels, not verified human gold",
        "scores_only_on_development_proxy_title_disjoint_split": True,
        "frozen_test_used": False, "phase3_confirmation_used": False,
        "source_hashes": provenance, "data_report": report,
        "hyperparameters": vars(args) | {"output": str(args.output)},
        "baseline": before, "history": history, "selected_epoch": best_result["epoch"],
        "best_development": best_result["validation"], "release_gates": gates,
        "eligible_for_deployment": False,
    }
    (args.output / "metrics.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("research candidate only; independent test unavailable; no VM changes", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--grad-accum", type=int, default=2)
    parser.add_argument("--lr", type=float, default=0.00002)
    parser.add_argument("--max-len", type=int, default=128)
    args = parser.parse_args()
    if args.epochs < 1 or args.epochs > 6 or args.grad_accum < 1 or args.batch < 1:
        parser.error("Invalid epoch, batch, or gradient accumulation values")
    args.output.mkdir(parents=True, exist_ok=True)
    rows, provenance = load_verified_development()
    train_rows, valid_rows, report = split_development(rows, args.seed)
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    if args.audit_only:
        (args.output / "data_audit.json").write_text(
            json.dumps({"provenance": provenance, "data_report": report}, indent=2) + "\n")
        return
    train(args, train_rows, valid_rows, report, provenance)


if __name__ == "__main__":
    main()
