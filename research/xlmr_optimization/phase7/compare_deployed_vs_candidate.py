"""Paired development-only comparison: repo's deployed ONNX vs Phase 7 adapter.

Uses exactly the SAME 50 held-out Phase 7 development reviews, in the same
order and with identical frozen Claude-v1 labels. Does not tune, retrain,
call a live VM, read the final test, or publish any review text.
Run from repo root with --artifact-dir (containing Phase 7 metrics/delta).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys
from math import comb

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))

from train_xlmr_research import (BASE, LABELS, load_verified_development,
                                 split_development, evaluate, score)
from defaketive_sentiment.transformer_sentiment import TransformerSentimentClassifier


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def predict_candidate(artifact, metric, rows):
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    revision = metric["data_report"]["base_revision"]
    if not revision or len(revision) != 40:
        raise RuntimeError("Phase 7 checkpoint revision not pinned")
    tokenizer = AutoTokenizer.from_pretrained(
        BASE, revision=revision, use_fast=False, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, revision=revision, trust_remote_code=False)
    actual = [str(model.config.id2label[i]).lower() for i in range(3)]
    if actual != list(LABELS):
        raise RuntimeError("Wrong model class order: " + repr(actual))

    delta = load_file(str(artifact / "adapter_delta.safetensors"))
    expected = {n for n, _ in model.named_parameters()
                if n.startswith(("roberta.encoder.layer.10.",
                                 "roberta.encoder.layer.11.", "classifier."))}
    if set(delta) != expected:
        raise RuntimeError(
            "Adapter keys don't exactly match expected last-two-layer tuning scope: "
            + repr({"missing": len(expected - set(delta)),
                    "extra": len(set(delta) - expected)}))
    load_result = model.load_state_dict(delta, strict=False)
    if load_result.unexpected_keys or set(load_result.missing_keys) & expected:
        raise RuntimeError("Saved adapter did not restore correctly")
    model.eval()
    torch.set_num_threads(4)
    prediction = []
    with torch.inference_mode():
        for start in range(0, len(rows), 16):
            chunk = rows[start:start + 16]
            tok = tokenizer([r["text"] for r in chunk],
                            padding=True, truncation=True, max_length=128,
                            return_tensors="pt")
            prediction.extend(model(**tok).logits.argmax(-1).cpu().tolist())
    # Also independently rederive metrics using the original Phase 7 evaluator.
    actual_eval = evaluate(model, tokenizer, rows, torch.device("cpu"), 128)
    recorded = metric["best_development"]
    if actual_eval["natural_dev"] != recorded["natural_dev"]:
        raise RuntimeError(
            "Regenerated candidate predictions do not reproduce the locked "
            "Phase 7 metrics; model revision, weight delta, or split differs: "
            + repr({"regenerated": actual_eval["natural_dev"],
                    "recorded": recorded["natural_dev"]}))
    return prediction, actual_eval


def paired_subsets(rows, y, old, new):
    sections = {
        "same_phase7_validation_50": list(range(len(rows))),
        "non_no_opinion": [i for i, r in enumerate(rows)
                          if not r["no_opinion"]],
        "no_opinion": [i for i, r in enumerate(rows)
                       if r["no_opinion"]],
        "filipino_taglish": [i for i, r in enumerate(rows)
                             if r["language"] in ("filipino", "taglish")],
        "english": [i for i, r in enumerate(rows)
                    if r["language"] == "english"],
    }
    report = {}
    for name, indices in sections.items():
        if not indices:
            continue
        labels = [y[i] for i in indices]
        deployed = [old[i] for i in indices]
        candidate = [new[i] for i in indices]
        report[name] = {
            "n": len(indices),
            "reference_support": dict(collections.Counter(LABELS[c] for c in labels)),
            "deployed": score(labels, deployed),
            "phase7": score(labels, candidate),
            "paired_correctness": {
                "both_correct": sum(old[i] == y[i] and new[i] == y[i] for i in indices),
                "both_wrong": sum(old[i] != y[i] and new[i] != y[i] for i in indices),
                "only_deployed_correct": sum(old[i] == y[i] and new[i] != y[i] for i in indices),
                "only_phase7_correct": sum(old[i] != y[i] and new[i] == y[i] for i in indices),
                "prediction_disagreements": sum(old[i] != new[i] for i in indices),
            },
        }
        report[name]["macro_f1_delta_phase7_minus_deployed"] = round(
            report[name]["phase7"]["macro_f1"] - report[name]["deployed"]["macro_f1"], 4)
    return report


def uncertainty(rows, y, old, new):
    """Cluster bootstrap by normalized listing-title group; explanatory only."""
    groups = sorted({r["group"] for r in rows})
    group_members = {
        group: [i for i, r in enumerate(rows) if r["group"] == group]
        for group in groups
    }
    rng = np.random.default_rng(20261116)
    changes = []
    for _ in range(1500):
        sample = rng.choice(groups, size=len(groups), replace=True)
        ix = [i for group in sample for i in group_members[group]]
        a = score([y[i] for i in ix], [old[i] for i in ix])["macro_f1"]
        b = score([y[i] for i in ix], [new[i] for i in ix])["macro_f1"]
        changes.append(b - a)
    wins = sum(o != truth and n == truth for truth, o, n in zip(y, old, new))
    losses = sum(o == truth and n != truth for truth, o, n in zip(y, old, new))
    n = wins + losses
    if n:
        # Exact two-sided binomial version of McNemar's matched-pair test.
        tail = sum(comb(n, k) for k in range(min(wins, losses) + 1)) / (2 ** n)
        p = min(1., 2. * tail)
    else:
        p = 1.0
    return {
        "paired_mcnemar_exact_two_sided_p": round(p, 6),
        "discordant_phase7_wins": wins,
        "discordant_deployed_wins": losses,
        "group_bootstrap_macro_f1_delta_95pct_ci": [
            round(float(x), 4) for x in np.quantile(changes, [0.025, 0.975])],
        "bootstrap_title_group_count": len(groups),
        "interpretation": "Descriptive only. 50 Claude-AI-labelled reviews and 12 title-proxy groups are too small to justify production replacement, even if p appears small.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-dir", type=pathlib.Path, required=True)
    p.add_argument("--output-dir", type=pathlib.Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metric = json.loads((args.artifact_dir / "metrics.json").read_text())
    if metric["status"] != "research_only_not_approved_for_vm_or_production":
        raise RuntimeError("Wrong candidate run")
    if metric["hyperparameters"]["seed"] != 20261116 or metric["hyperparameters"]["max_len"] != 128:
        raise RuntimeError("Phase 7 split or tokenization settings changed")
    if metric["eligible_for_deployment"] is not False:
        raise RuntimeError("Candidate release flag unexpectedly changed")

    source, provenance = load_verified_development()
    for section, fields in provenance.items():
        for attr in ("original_sha256", "ai_label_sha256"):
            if metric["source_hashes"][section][attr] != fields[attr]:
                raise RuntimeError("Source annotation files differ from trained candidate")
    training, validation, audit = split_development(source, 20261116)
    for field in ("training_rows", "validation_rows", "train_label_counts",
                  "validation_label_counts", "training_title_groups",
                  "validation_title_groups"):
        if audit[field] != metric["data_report"][field]:
            raise RuntimeError("Phase 7 data split changed: " + field)
    if len(validation) != 50:
        raise RuntimeError("Unexpected Phase 7 validation size")
    if len({r["group"] for r in validation}) != 12:
        raise RuntimeError("Unexpected Phase 7 validation groups")

    model_dir = ROOT / "backend" / "sentiment-analysis" / "models" / "sentiment_onnx" / "xlmr_firecs_v1"
    deployed = TransformerSentimentClassifier(model_dir=model_dir, threads=1)
    if deployed.manifest["model_version"] != "defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2":
        raise RuntimeError("Configured deployed model version changed")
    if deployed.labels != list(LABELS):
        raise RuntimeError("Deployed model class mapping changed")
    y = [LABELS.index(r["label"]) for r in validation]
    old = [LABELS.index(deployed.predict(r["text"])["label"]) for r in validation]
    new, regenerated = predict_candidate(args.artifact_dir, metric, validation)
    result = {
        "status": "paired_comparison_completed_research_only",
        "meaning": "Both actual trained inference artifacts evaluated on identical Phase 7 held-out development examples, not on an independently human-verified test.",
        "same_review_ids_for_both": True,
        "same_reference_labels_for_both": True,
        "source_reference": "frozen Claude v1 AI annotation, not independently human confirmed",
        "frozen_final_test_used": False,
        "phase3_confirmation_used": False,
        "no_vm_access_or_deployment": True,
        "configured_deployed_model_version": deployed.model_version,
        "configured_deployed_onnx_sha256": sha256(model_dir / "model.onnx"),
        "candidate_source_run": "https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43734828440",
        "candidate_base_revision": metric["data_report"]["base_revision"],
        "candidate_provenance_hashes": metric["source_hashes"],
        "candidate_reproduces_previous_50_review_score": True,
        "datasets": paired_subsets(validation, y, old, new),
        "paired_uncertainty": uncertainty(validation, y, old, new),
        "limits": [
            "Same 50 reviews and 12 normalized-title proxy groups only.",
            "Labels came from Claude policy-v1 annotation and remain unverified by independent humans.",
            "Product-ID grouping was not possible; near-duplicate and semantic leakage not fully excluded.",
            "Phase 7 is a full-precision pretrained model with last-two-layer fine-tuning; deployed model is pruned/quantized ONNX.",
            "Live VM runtime SHA/version not independently queried; compare exact current repository deployment artifact.",
            "Phase 7 validation was used for model checkpoint selection: not a fresh unbiased final test.",
            "Model accuracy alone does not validate hazard checker or product-specific conclusions.",
        ],
        "decision": "Do not replace live VM solely on this development comparison; require fresh independent authorized, product-ID-disjoint human-checked evaluation and app-level safety tests.",
    }
    (args.output_dir / "paired_comparison.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    main_set = result["datasets"]["same_phase7_validation_50"]
    print(json.dumps({
        "model_versions": {"deployed": deployed.model_version, "candidate": "phase7 last-two-layer adapter"},
        "dataset": "identical 50 Phase 7 dev reviews, Claude-v1 labels",
        "deployed_accuracy": main_set["deployed"]["accuracy"],
        "deployed_macro_f1": main_set["deployed"]["macro_f1"],
        "deployed_neutral_f1": main_set["deployed"]["classes"]["neutral"]["f1"],
        "deployed_negative_recall": main_set["deployed"]["classes"]["negative"]["recall"],
        "candidate_accuracy": main_set["phase7"]["accuracy"],
        "candidate_macro_f1": main_set["phase7"]["macro_f1"],
        "candidate_neutral_f1": main_set["phase7"]["classes"]["neutral"]["f1"],
        "candidate_negative_recall": main_set["phase7"]["classes"]["negative"]["recall"],
        "paired_disagreements": main_set["paired_correctness"],
        "confidence": result["paired_uncertainty"],
        "production_ready": False,
    }, indent=2))


if __name__ == "__main__":
    main()
