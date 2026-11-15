"""Compare deployment artifacts as DISTINCT artifacts: scores, label agreement, cold start, memory, latency, throughput, size.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/onnx_benchmark.py <tag>=<model.onnx>|<tokenizer.json> [<tag>=...] [--skip-accuracy] [--skip-perf] [--sets market_test_v3,firecs_test]

Accuracy pass: every review scored on its own (as the app does; the int8 activation scales depend on the batch), 8 worker processes, predictions saved as
predictions/<tag>__<set>.csv and scored by metrics_x. Performance pass, afterwards and one artifact at a time in a FRESH process: ONNX Runtime with 1 intra-op
thread (the production setting), cold start (session creation to first answer), resident memory after load and at peak, median / p95 latency over 200
single reviews, reviews per second, file size. Performance on this PC is NOT the VM: the same pass must be repeated on the VM (read-only, outside the
service) before any deployment claim. Writes results/onnx_benchmark.json.
"""
import csv, json, multiprocessing as mp, pathlib, subprocess, sys, time
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata  # noqa: E402
from inference import rows_of  # noqa: E402

_s = {}


def _init(onnx, tokfile):
    import onnxruntime as ort
    from tokenizers import Tokenizer
    o = ort.SessionOptions()
    o.intra_op_num_threads = 1
    o.inter_op_num_threads = 1
    o.enable_cpu_mem_arena = False
    o.enable_mem_pattern = False
    _s["sess"] = ort.InferenceSession(onnx, o, providers=["CPUExecutionProvider"])
    t = Tokenizer.from_file(tokfile)
    t.no_padding()
    t.enable_truncation(max_length=128)
    _s["tok"] = t


def score(text):
    e = _s["tok"].encode(str(text or "").strip())
    lg = _s["sess"].run(["logits"], {"input_ids": np.array([e.ids], dtype=np.int64), "attention_mask": np.array([e.attention_mask], dtype=np.int64)})[0][0].astype(np.float64)
    p = np.exp(lg - lg.max())
    return (p / p.sum()).tolist()


def _work(texts):
    return [score(t) for t in texts]


def accuracy(tag, onnx, tokfile, sets):
    for name in sets:
        rows = rows_of(name)
        texts = [r["text"] for r in rows]
        w = 8
        chunks = [texts[i::w * 4] for i in range(w * 4)]
        with mp.Pool(w, initializer=_init, initargs=(onnx, tokfile)) as pool:
            parts = pool.map(_work, chunks)
        P = np.zeros((len(texts), 3))
        for i, part in enumerate(parts):
            P[i::w * 4] = np.array(part)
        with open(xdata.X / "predictions" / f"{tag}__{name}.csv", "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["id", "label", "p_neg", "p_neu", "p_pos", "pred"])
            for r, q in zip(rows, P):
                wr.writerow([r["id"], r["label"], *[f"{v:.6f}" for v in q], xdata.LABELS[int(q.argmax())]])


PERF = r'''
import json, sys, time, psutil, numpy as np
onnx, tokfile, texts_file = sys.argv[1:4]
texts = json.load(open(texts_file))
proc = psutil.Process()
rss0 = proc.memory_info().rss / 1e6
t0 = time.perf_counter()
import onnxruntime as ort
from tokenizers import Tokenizer
o = ort.SessionOptions(); o.intra_op_num_threads = 1; o.inter_op_num_threads = 1; o.enable_cpu_mem_arena = False; o.enable_mem_pattern = False
sess = ort.InferenceSession(onnx, o, providers=["CPUExecutionProvider"])
tok = Tokenizer.from_file(tokfile); tok.no_padding(); tok.enable_truncation(max_length=128)
def run(t):
    e = tok.encode(t.strip())
    return sess.run(["logits"], {"input_ids": np.array([e.ids], dtype=np.int64), "attention_mask": np.array([e.attention_mask], dtype=np.int64)})
run(texts[0]); cold = time.perf_counter() - t0
rss_load = proc.memory_info().rss / 1e6
lat = []
peak = rss_load
for t in texts:
    a = time.perf_counter(); run(t); lat.append((time.perf_counter() - a) * 1000)
    peak = max(peak, proc.memory_info().rss / 1e6)
print(json.dumps({"cold_start_s": round(cold, 2), "rss_before_mb": round(rss0, 1), "rss_after_load_mb": round(rss_load, 1), "peak_rss_mb": round(peak, 1), "latency_ms_median": round(float(np.median(lat)), 1),
                  "latency_ms_p95": round(float(np.percentile(lat, 95)), 1), "reviews_per_second_1_thread": round(1000 / float(np.mean(lat)), 1)}))
'''


def perf(onnx, tokfile):
    texts = [r["text"] for r in rows_of("market_test_v3")][:200]
    tf = xdata.X / "results" / "_perf_texts.json"
    tf.write_text(json.dumps(texts))
    out = subprocess.run([sys.executable, "-c", PERF, onnx, tokfile, str(tf)], capture_output=True, text=True)
    last = [l for l in out.stdout.splitlines() if l.startswith("{")]
    res = json.loads(last[-1])
    res["file_mb"] = round(pathlib.Path(onnx).stat().st_size / 1e6, 1)
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sets = ["market_test_v3", "firecs_test", "market_gold200", "market_heldout100"]
    if "--sets" in sys.argv:
        sets = sys.argv[sys.argv.index("--sets") + 1].split(",")
        args = [a for a in args if a != ",".join(sets)]
    out = {}
    for spec in args:
        tag, rest = spec.split("=", 1)
        onnx, tokfile = rest.split("|", 1)
        if "--skip-accuracy" not in sys.argv:
            accuracy(tag, onnx, tokfile, sets)
        if "--skip-perf" in sys.argv:
            continue
        out[tag] = perf(onnx, tokfile)
        print(tag, out[tag], flush=True)
    path = xdata.X / "results" / "onnx_benchmark.json"
    old = json.load(open(path)) if path.exists() else {}
    old.update(out)
    json.dump(old, open(path, "w"), indent=1)
