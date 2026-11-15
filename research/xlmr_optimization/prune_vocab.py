"""Vocabulary pruning of a fine-tuned XLM-R checkpoint (keeps the pieces that occur in the study's corpora, all single characters and the special tokens).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/prune_vocab.py <checkpoint dir> <output dir>

The 250,002-piece vocabulary makes the embedding table 192 M of the 278 M parameters. Reviews use a small part of it. The tokenizer (Unigram) is rebuilt with
the kept pieces in their original order, so the special tokens keep ids 0 to 3 and padding id 1 (RoBERTa position ids depend on it); the embedding table is
sliced to the same rows. Texts that need a removed piece are segmented with the remaining pieces (single characters are always kept), so a rare word can
change its tokens: the label agreement with the unpruned checkpoint is measured separately (onnx_benchmark.py), not assumed.
Corpora used to choose the kept pieces: FiReCS train and test, every team-labelled marketplace file, the 10,000-review pool and the review text of the
production database copy. Writes <output dir>/{model.safetensors, config.json, tokenizer.json, tokenizer_config.json, prune_report.json}.
"""
import json, pathlib, sqlite3, sys
import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer, PreTrainedTokenizerFast  # noqa: E402


def corpus():
    texts = [r["text"] for s in ("train", "test") for r in xdata.load_firecs(s)]
    for rows in xdata.load_marketplace().values():
        texts += [r["text"] for r in rows]
    import csv
    texts += [r["review_text"] for r in csv.DictReader(open(xdata.ROOT / "evaluation" / "review_pool_10000.csv", encoding="utf-8-sig"))]
    import glob
    db = glob.glob("D:/defaketive-backups/predeploy-*/defaketive.db")
    if db:
        con = sqlite3.connect(f"file:{db[0]}?mode=ro", uri=True)
        texts += [t for (t,) in con.execute("SELECT content FROM reviews WHERE length(content) >= 3") if t]
    return texts


def main(src, dst):
    dst = pathlib.Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(src)
    model = AutoModelForSequenceClassification.from_pretrained(src)
    spec = json.loads(tok.backend_tokenizer.to_str())
    vocab = spec["model"]["vocab"]  # [[piece, score], ...], index = id
    texts = corpus()
    used = set()
    for i in range(0, len(texts), 2000):
        for ids in tok(texts[i:i + 2000], truncation=True, max_length=128)["input_ids"]:
            used.update(ids)
    keep = set(range(4)) | used | {len(vocab) + k for k in range(0)}
    keep |= {i for i, (piece, _) in enumerate(vocab) if len(piece.replace("\u2581", "")) <= 1}  # every single character (with or without the word marker)
    added = {a["content"]: a["id"] for a in spec["added_tokens"]}
    keep |= set(added.values())
    keep = sorted(k for k in keep if k < len(vocab) or k in added.values())
    # <mask> (and any added token) lives beyond the Unigram list in XLM-R: it is re-added at the end
    unigram_keep = [k for k in keep if k < len(vocab)]
    remap = {old: new for new, old in enumerate(unigram_keep)}
    spec["model"]["vocab"] = [vocab[k] for k in unigram_keep]
    spec["model"]["unk_id"] = remap[spec["model"]["unk_id"]]
    n = len(unigram_keep)
    for a in spec["added_tokens"]:
        a["id"] = remap[a["id"]] if a["id"] in remap else n  # <mask> follows the last piece
    for tok_name, info in (spec.get("post_processor") or {}).get("special_tokens", {}).items():
        info["ids"] = [remap[i] if i in remap else n for i in info["ids"]]
    pp = spec.get("post_processor") or {}
    if pp.get("type") == "RobertaProcessing":
        pp["sep"][1] = remap[pp["sep"][1]]; pp["cls"][1] = remap[pp["cls"][1]]
    new_tok = PreTrainedTokenizerFast(tokenizer_object=__import__("tokenizers").Tokenizer.from_str(json.dumps(spec)), bos_token="<s>", eos_token="</s>", sep_token="</s>", cls_token="<s>", unk_token="<unk>", pad_token="<pad>", mask_token="<mask>")
    emb = model.roberta.embeddings.word_embeddings.weight.data
    rows_new = torch.cat([emb[unigram_keep], emb[[added["<mask>"]]]]) if "<mask>" in added else emb[unigram_keep]
    model.roberta.embeddings.word_embeddings = torch.nn.Embedding.from_pretrained(rows_new.clone(), freeze=False, padding_idx=1)
    model.config.vocab_size = rows_new.shape[0]
    model.save_pretrained(dst)
    new_tok.save_pretrained(dst)
    (dst / "tokenizer.json").write_text(json.dumps(spec), encoding="utf-8")
    report = {"source": str(src), "vocab_before": len(vocab), "vocab_after": int(rows_new.shape[0]), "corpus_texts": len(texts), "pieces_used_in_corpus": len(used),
              "parameters_before": int(sum(p.numel() for p in AutoModelForSequenceClassification.from_pretrained(src).parameters())), "parameters_after": int(sum(p.numel() for p in model.parameters()))}
    json.dump(report, open(dst / "prune_report.json", "w"), indent=1)
    print(report)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
