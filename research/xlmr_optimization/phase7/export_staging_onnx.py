"""Convert the locked Phase 7 adapter into an OFFLINE RESEARCH ONNX candidate.

No VM connection, no production override, no inference endpoint, no customer
reviews embedded in artifact. Never mark qualified_for_integration=true.

Usage:
  python research/xlmr_optimization/phase7/export_staging_onnx.py \
    --artifact /tmp/phase7-original --output /tmp/phase7-stage

Requires torch==2.5.1, transformers==4.46.3, safetensors, tokenizers,
onnx and onnxruntime. Do not run this inside the live production service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from train_xlmr_research import BASE, LABELS, load_verified_development, split_development, score


def sha256(path):
    dig = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            dig.update(chunk)
    return dig.hexdigest()


def load_phase7(artifact_dir, metrics):
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    revision = metrics["data_report"]["base_revision"]
    if not revision or len(revision) != 40:
        raise ValueError("Missing pinned model source revision")
    if metrics["eligible_for_deployment"] or metrics["frozen_test_used"]:
        raise ValueError("Not a Phase 7 research-only artifact")
    if metrics["hyperparameters"]["max_len"] != 128:
        raise ValueError("Unexpected Phase 7 maximum token length")
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, revision=revision, trust_remote_code=False)
    slow = AutoTokenizer.from_pretrained(
        BASE, revision=revision, trust_remote_code=False, use_fast=False)
    fast = AutoTokenizer.from_pretrained(
        BASE, revision=revision, trust_remote_code=False, use_fast=True)
    class_order = [str(model.config.id2label[i]).casefold() for i in range(3)]
    if class_order != list(LABELS):
        raise ValueError("Incorrect model class label order")
    delta = load_file(str(artifact_dir / "adapter_delta.safetensors"))
    expected = {name for name, _ in model.named_parameters()
                if name.startswith((
                    "roberta.encoder.layer.10.", "roberta.encoder.layer.11.",
                    "classifier."))}
    if set(delta) != expected:
        raise ValueError("Adapter keys do not match the frozen Phase 7 tuning scope")
    result = model.load_state_dict(delta, strict=False)
    if result.unexpected_keys or set(result.missing_keys) & expected:
        raise ValueError("Adapter not restored precisely")
    torch.set_num_threads(4)
    model.cpu().eval()
    return model, slow, fast, revision


class OnnxWrapper:
    @staticmethod
    def wrap(model):
        import torch

        class WithEmbedding(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.model = model

            def forward(self, input_ids, attention_mask):
                out = self.model.roberta(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    return_dict=True)
                hidden = out.last_hidden_state
                return self.model.classifier(hidden), hidden
        return WithEmbedding().eval()


def validate_tokenizers(slow, fast, rows):
    for row in rows:
        s = slow(row["text"], add_special_tokens=True, truncation=True, max_length=128)
        f = fast(row["text"], add_special_tokens=True, truncation=True, max_length=128)
        if s["input_ids"] != f["input_ids"]:
            raise ValueError("Fast runtime tokenizer disagrees with Phase 7 slow tokenizer")


def export(model, output_dir):
    import torch
    import onnx
    from onnxruntime.quantization import quantize_dynamic, QuantType

    fp32 = output_dir / "intermediate_fp32.onnx"
    q8 = output_dir / "model.onnx"
    ids = torch.tensor([[0, 100, 200, 300, 2]], dtype=torch.long)
    masks = torch.ones_like(ids)
    torch.onnx.export(
        OnnxWrapper.wrap(model), (ids, masks), str(fp32),
        input_names=["input_ids", "attention_mask"],
        output_names=["logits", "hidden_states"],
        opset_version=17, dynamo=False,
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "logits": {0: "batch"},
            "hidden_states": {0: "batch", 1: "sequence"},
        })
    checked = onnx.load(str(fp32))
    onnx.checker.check_model(checked)
    if [x.name for x in checked.graph.output] != ["logits", "hidden_states"]:
        raise ValueError("Export lost sentiment logits or embedding output")
    del checked
    quantize_dynamic(str(fp32), str(q8), weight_type=QuantType.QInt8)
    onnx.checker.check_model(str(q8))
    # Never include an extra fp32 copy in the staging artifact.
    fp32.unlink()
    return q8


def run_eval(model, slow, output_dir, rows):
    import torch
    import onnxruntime as ort
    import psutil
    from tokenizers import Tokenizer

    t0 = time.perf_counter()
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    opts.inter_op_num_threads = 1
    opts.enable_cpu_mem_arena = False
    opts.enable_mem_pattern = False
    session = ort.InferenceSession(str(output_dir / "model.onnx"), opts,
                                   providers=["CPUExecutionProvider"])
    outputs = [o.name for o in session.get_outputs()]
    if "logits" not in outputs or "hidden_states" not in outputs:
        raise ValueError("VM-required ONNX model outputs missing")
    tok = Tokenizer.from_file(str(output_dir / "tokenizer.json"))
    tok.no_padding()
    tok.enable_truncation(max_length=128)
    load_seconds = round(time.perf_counter() - t0, 3)
    rss_loaded = round(psutil.Process().memory_info().rss / 1024**2, 2)
    baseline, qpred = [], []
    max_diff = 0.0
    latency = []
    for row in rows:
        text = row["text"]
        inputs = slow(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.inference_mode():
            baseline_logit = model(**inputs).logits[0].detach().cpu().numpy()
        encoded = tok.encode(text)
        t1 = time.perf_counter()
        onnx_logit, emb = session.run(
            ["logits", "hidden_states"],
            {"input_ids": np.array([encoded.ids], dtype=np.int64),
             "attention_mask": np.array([encoded.attention_mask], dtype=np.int64)})
        latency.append((time.perf_counter() - t1) * 1000)
        if emb.shape != (1, len(encoded.ids), 768):
            raise ValueError("Embedding interface is not 1 x token count x 768")
        baseline.append(int(baseline_logit.argmax()))
        qpred.append(int(onnx_logit[0].argmax()))
        max_diff = max(max_diff, float(np.max(abs(baseline_logit - onnx_logit[0]))))
    gold = [LABELS.index(row["label"]) for row in rows]
    result = {
        "source": "Phase 7's original AI-assisted development-validation set, NOT independent test",
        "num_reviews": len(rows),
        "class_order": LABELS,
        "pytorch_full_precision": score(gold, baseline),
        "onnx_int8": score(gold, qpred),
        "predictions_matching_pytorch": sum(a == b for a, b in zip(baseline, qpred)),
        "max_absolute_logit_difference": round(max_diff, 4),
        "runtime": {
            "model_load_seconds_on_runner": load_seconds,
            "rss_mb_after_loading_both_pytorch_and_onnx": rss_loaded,
            "median_onnx_inference_ms": round(float(np.median(latency)), 1),
            "p95_onnx_inference_ms": round(float(np.percentile(latency, 95)), 1),
            "not_a_vm_benchmark": True,
        },
    }
    if result["pytorch_full_precision"] != json.loads(
            (output_dir / "expected_pytorch_metrics.json").read_text())["natural_dev"]:
        raise ValueError("Restored candidate does not reproduce recorded development metrics")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact", required=True, type=pathlib.Path)
    p.add_argument("--output", required=True, type=pathlib.Path)
    a = p.parse_args()
    out = a.output
    out.mkdir(parents=True, exist_ok=False)
    metrics = json.loads((a.artifact / "metrics.json").read_text())
    if metrics["eligible_for_deployment"] is not False or metrics["frozen_test_used"]:
        raise ValueError("Release gate violation")
    rows, provenance = load_verified_development()
    for section in provenance:
        for key in ("original_sha256", "ai_label_sha256"):
            if provenance[section][key] != metrics["source_hashes"][section][key]:
                raise ValueError("Source data changed since training")
    train_rows, validation, audit = split_development(rows, metrics["hyperparameters"]["seed"])
    if len(validation) != 50 or len({r["group"] for r in validation}) != 12:
        raise ValueError("Development split has changed")
    if audit["validation_label_counts"] != metrics["data_report"]["validation_label_counts"]:
        raise ValueError("Wrong development validation labels")
    model, slow, fast, revision = load_phase7(a.artifact, metrics)
    validate_tokenizers(slow, fast, validation)
    fast.backend_tokenizer.save(str(out / "tokenizer.json"))
    (out / "expected_pytorch_metrics.json").write_text(json.dumps(metrics["best_development"]))
    onnx_path = export(model, out)
    validation_result = run_eval(model, slow, out, validation)
    (out / "expected_pytorch_metrics.json").unlink()
    manifest = {
        "name": "xlmr_phase7_staging",
        "model_version": "research-xlmr-phase7-staging-int8-" + sha256(onnx_path)[:12],
        "stage": "research_staging_only",
        "qualified_for_integration": False,
        "eligible_for_deployment": False,
        "model_regulatory_or_safety_gate_passed": False,
        "text": "raw",
        "labels": list(LABELS),
        "max_length": 128,
        "outputs": ["logits", "hidden_states"],
        "source_training_run": "https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43734828440",
        "base_revision": revision,
        "files": {name: sha256(out / name) for name in ["model.onnx", "tokenizer.json"]},
        "model_size_mb": round(onnx_path.stat().st_size / 1024**2, 2),
        "release_blocks": [
            "No independent human-verified product-disjoint >=0.80 macro-F1.",
            "Hazard model v6 gates predictions by original ONNX sentiment SHA.",
            "Neither actual Azure VM memory nor end-to-end app tested.",
            "No validated Filipino/Taglish natural neutral generalization.",
            "Product-level conclusions not revalidated.",
        ],
        "diagnostics": validation_result,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    summary = {k: manifest[k] for k in ("name", "model_version", "stage",
                                       "qualified_for_integration", "model_size_mb",
                                       "release_blocks")}
    summary["diagnostics"] = {
        "pt_macro_f1": validation_result["pytorch_full_precision"]["macro_f1"],
        "onnx_macro_f1": validation_result["onnx_int8"]["macro_f1"],
        "agreement_n": validation_result["predictions_matching_pytorch"],
        "validation_n": validation_result["num_reviews"],
        "load_seconds_runner": validation_result["runtime"]["model_load_seconds_on_runner"],
        "rss_mb_both_models_runner": validation_result["runtime"]["rss_mb_after_loading_both_pytorch_and_onnx"],
    }
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
