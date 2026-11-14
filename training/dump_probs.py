"""Save the trained model's probabilities for the validation and test rows (same split as train_label_model.py)."""
import json, pathlib, sys
import numpy as np, torch
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import train_label_model as T
from train_label_model import by_product, predict, read_batch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
run = pathlib.Path(sys.argv[1]); torch.set_num_threads(12)
train_file = sys.argv[2] if len(sys.argv) > 2 else "evaluation/annotated/train_all.csv"
test_file = sys.argv[3] if len(sys.argv) > 3 else "evaluation/annotated/test_all.csv"
if len(sys.argv) > 4 and sys.argv[4] == "delivery": T.FLAGS = T.BASE_FLAGS + ("delivery",)
train = read_batch(pathlib.Path(train_file))
_, valid = by_product(train, 12, "valid")
test = read_batch(pathlib.Path(test_file))
tok = AutoTokenizer.from_pretrained(run / "model"); model = AutoModelForSequenceClassification.from_pretrained(run / "model")
out = {}
for name, rows in (("valid", valid), ("test", test)):
    p = predict(model, rows, tok, 160)
    out[name] = [{"id": r["id"], "y": r["y"], "p": [float(x) for x in p[i]]} for i, r in enumerate(rows)]
json.dump(out, open(run / "probs.json", "w"))
print({k: len(v) for k, v in out.items()})
