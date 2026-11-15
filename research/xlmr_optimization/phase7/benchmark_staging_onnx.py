"""Isolated CPU memory/performance smoke test for research ONNX staging candidate.

Runs after PyTorch export exits so measured RSS excludes model reconstruction.
Reports ONLY aggregate memory and latency, using synthetic texts. No real
reviews, no VM, no deployment, no read of credentials, no model qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time

import numpy as np
import psutil
import onnxruntime as ort
from tokenizers import Tokenizer


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate",type=pathlib.Path,required=True)
    a=ap.parse_args()
    folder=a.candidate
    manifest=json.loads((folder/"manifest.json").read_text())
    if manifest["qualified_for_integration"] or manifest["eligible_for_deployment"]:
        raise RuntimeError("Expected blocked research-only candidate")
    for name,digest in manifest["files"].items():
        if sha256(folder/name)!=digest:
            raise RuntimeError("Stage artifact hash mismatch")
    proc=psutil.Process()
    rss_before=proc.memory_info().rss/2**20
    t0=time.perf_counter()
    opts=ort.SessionOptions()
    opts.intra_op_num_threads=1
    opts.inter_op_num_threads=1
    opts.enable_cpu_mem_arena=False
    opts.enable_mem_pattern=False
    sess=ort.InferenceSession(str(folder/"model.onnx"),opts,
                               providers=["CPUExecutionProvider"])
    tok=Tokenizer.from_file(str(folder/"tokenizer.json"))
    tok.no_padding()
    tok.enable_truncation(max_length=128)
    load_s=time.perf_counter()-t0
    rss_loaded=proc.memory_info().rss/2**20
    assert [o.name for o in sess.get_outputs()]==["logits","hidden_states"]
    texts=[
        "Good quality. Works well and feels durable.",
        "I ordered this for my family but the device stopped working immediately.",
        "Adjustable settings and LED display.",
        "Okay lang. Hindi ko pa nagagamit.",
        "Pangit ang quality. Nasira agad.",
        "Very nice, mabilis dumating and sulit sa presyo.",
        "The color is blue and the cable is included.",
    ]*7
    latencies=[]
    peak=rss_loaded
    for txt in texts:
        z=tok.encode(txt)
        start=time.perf_counter()
        logits,emb=sess.run(["logits","hidden_states"],{
            "input_ids":np.array([z.ids],dtype=np.int64),
            "attention_mask":np.array([z.attention_mask],dtype=np.int64),
        })
        latencies.append((time.perf_counter()-start)*1000)
        if logits.shape!=(1,3) or emb.shape!=(1,len(z.ids),768):
            raise RuntimeError("Model output schema broken")
        peak=max(peak,proc.memory_info().rss/2**20)
    report={
      "model":manifest["model_version"],
      "runner_not_live_vm":True,
      "with_pytorch_unloaded":True,
      "rss_before_model_mb":round(rss_before,2),
      "rss_after_load_mb":round(rss_loaded,2),
      "peak_rss_mb":round(peak,2),
      "net_added_rss_mb":round(peak-rss_before,2),
      "load_seconds":round(load_s,2),
      "median_latency_ms":round(float(np.median(latencies)),2),
      "p95_latency_ms":round(float(np.percentile(latencies,95)),2),
      "synthetic_review_count":len(texts),
      "qualifies_for_deployment":False,
      "physical_memory_warning":"A 512 MB VM still needs separate measured VM-specific testing with the active application."
    }
    (folder/"isolated_cpu_benchmark.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
