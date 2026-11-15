"""Export a (pruned or unpruned) HF checkpoint to ONNX FP32 and to ONNX int8 (dynamic quantisation, weights int8), the same kind of artifact as the deployed one.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/export_onnx.py <checkpoint dir> <output dir>

Writes <output dir>/model_fp32.onnx, model_int8.onnx and tokenizer.json (copied from the checkpoint). Nothing is written under backend/ and nothing is deployed.
"""
import pathlib, shutil, sys
import torch
from transformers import AutoModelForSequenceClassification


class Wrap(torch.nn.Module):
    def __init__(self, m):
        super().__init__()
        self.m = m

    def forward(self, input_ids, attention_mask):
        return self.m(input_ids=input_ids, attention_mask=attention_mask).logits


def main(src, dst):
    src, dst = pathlib.Path(src), pathlib.Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    model = Wrap(AutoModelForSequenceClassification.from_pretrained(src).eval())
    ids = torch.tensor([[0, 100, 200, 300, 2], [0, 100, 2, 1, 1]])
    mask = torch.tensor([[1, 1, 1, 1, 1], [1, 1, 1, 0, 0]])
    fp32 = dst / "model_fp32.onnx"
    torch.onnx.export(model, (ids, mask), str(fp32), input_names=["input_ids", "attention_mask"], output_names=["logits"], opset_version=17, dynamo=False,
                      dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}, "logits": {0: "batch"}})
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(str(fp32), str(dst / "model_int8.onnx"), weight_type=QuantType.QInt8)
    # variants tried to recover the accuracy the plain int8 loses: per-channel weights, and selective quantisation (the last two encoder layers and the classifier stay FP32)
    quantize_dynamic(str(fp32), str(dst / "model_int8_perchannel.onnx"), weight_type=QuantType.QInt8, per_channel=True)
    import onnx
    graph = onnx.load(str(fp32)).graph
    skip = [n.name for n in graph.node if any(k in n.name for k in ("/layer.10/", "/layer.11/", "classifier"))]
    quantize_dynamic(str(fp32), str(dst / "model_int8_selective.onnx"), weight_type=QuantType.QInt8, nodes_to_exclude=skip)
    if (src / "tokenizer.json").exists():
        shutil.copy(src / "tokenizer.json", dst / "tokenizer.json")
    for f in ("model_fp32.onnx", "model_int8.onnx", "model_int8_perchannel.onnx", "model_int8_selective.onnx"):
        print(f, round((dst / f).stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
