"""Probabilities (negative, neutral, positive) of any candidate on any list of texts, plus predictions files.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/inference.py <model> <set> [<set> ...]

<model>: onnx_int8 (the deployed artifact, one review at a time exactly as the app runs it), cardiff_fp32 (the public base checkpoint the
deployed model was built from, zero-shot), or hf:<directory> (a fine-tuned checkpoint of this study).
<set>: firecs_test, firecs_train, or a marketplace file name (market_test_v3, ...). High and low confidence rows are all predicted; the
metrics script filters. Output: predictions/<model>__<set>.csv (id, label, p_neg, p_neu, p_pos, pred).
"""
import csv, multiprocessing as mp, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata  # noqa: E402

ONNX_DIR = xdata.ROOT / "backend" / "sentiment-analysis" / "models" / "sentiment_onnx" / "xlmr_firecs_v1"
CARDIFF = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_clf = None


def _init(model_dir):
    global _clf
    sys.path.insert(0, str(xdata.ROOT / "backend" / "sentiment-analysis"))
    from defaketive_sentiment.transformer_sentiment import TransformerSentimentClassifier
    _clf = TransformerSentimentClassifier(model_dir, threads=1)


def _work(texts):
    out = []
    for t in texts:
        p = _clf.predict(t)["probabilities"]
        out.append([p["negative"], p["neutral"], p["positive"]])
    return out


def probs_onnx(texts, model_dir=ONNX_DIR, workers=8):
    chunks = [texts[i::workers * 4] for i in range(workers * 4)]
    with mp.Pool(workers, initializer=_init, initargs=(str(model_dir),)) as pool:
        parts = pool.map(_work, chunks)
    out = np.zeros((len(texts), 3))
    for i, part in enumerate(parts):
        out[i::workers * 4] = np.array(part)
    return out


def probs_hf(texts, path, batch=48, max_length=128, threads=12):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    torch.set_num_threads(threads)
    local = path == CARDIFF
    tok = AutoTokenizer.from_pretrained(path, local_files_only=local)
    model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=local).eval()
    order = np.argsort([len(t) for t in texts])
    out = np.zeros((len(texts), 3))
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            idx = order[i:i + batch]
            enc = tok([texts[j] for j in idx], padding=True, truncation=True, max_length=max_length, return_tensors="pt")
            out[idx] = torch.softmax(model(**enc).logits.float(), -1).numpy()
    return out


def rows_of(name):
    if name in ("market_val", "firecs_val"):  # the fixed validation splits of splits.py (never used for training)
        import json
        ids = set(json.load(open(xdata.DATA / "splits.json"))[name])
        src = xdata.load_marketplace()["market_train_v3"] if name == "market_val" else xdata.load_firecs("train")
        return [r for r in src if r["id"] in ids]
    if name.startswith("firecs_"):
        return xdata.load_firecs(name.split("_", 1)[1])
    return xdata.load_marketplace()[name]


def predict(model, name):
    rows = rows_of(name)
    texts = [r["text"] for r in rows]
    p = probs_onnx(texts) if model == "onnx_int8" else probs_hf(texts, CARDIFF if model == "cardiff_fp32" else model[3:])
    tag = pathlib.Path(model[3:]).parent.name if model.startswith("hf:") else model  # a checkpoint is named by its run directory
    target = xdata.X / "predictions" / f"{tag}__{name}.csv"
    with open(target, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id", "label", "p_neg", "p_neu", "p_pos", "pred"])
        for r, q in zip(rows, p):
            w.writerow([r["id"], r["label"], *[f"{v:.6f}" for v in q], xdata.LABELS[int(q.argmax())]])
    return target


if __name__ == "__main__":
    for s in sys.argv[2:]:
        print(predict(sys.argv[1], s), flush=True)
