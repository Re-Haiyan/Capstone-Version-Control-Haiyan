"""Error taxonomy of a prediction file (default: the deployed ONNX int8 model): confusion cells, text-feature tags, rates and examples.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/error_analysis.py predictions/onnx_int8__market_test_v3.csv [...]

Tags are transparent heuristics (regular expressions on the text, the star rating where the set has one), not annotations; a review can carry
several. Labels are team-supplied and unverified (marketplace sets) or published (FiReCS): the "error" is a DISAGREEMENT with the label,
and a disagreement may be the label's fault. Writes results/error_analysis__<model>__<set>.json. The data contain no reviewer names.
"""
import csv, json, pathlib, re, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata, metrics_x  # noqa: E402

TAGS = {
    "template_or_feature_list": re.compile(r"(?:best feature|product quality|performance|sound quality|suitability|ease of cleaning|durability)\s*:|^(?:[^.!?]{3,60},\s*){3,}", re.I),
    "contrast_marker (mixed opinion?)": re.compile(r"\b(?:pero|but|kaso|however|although|though|kaya lang|habang|except|ngunit|datapwat)\b", re.I),
    "delivery_or_seller_mention": re.compile(r"\b(?:deliver\w*|rider|shipping|shipped|courier|packag\w*|packing|seller|parcel|dumating|nadeliver|box)\b", re.I),
    "negation": re.compile(r"\b(?:hindi|di|not|no|never|wala|walang|ayaw|cannot|can'?t|won'?t|doesn'?t|didn'?t|isn'?t|wasn'?t)\b", re.I),
    "defect_or_failure_words": re.compile(r"\b(?:sira|basag|broken|defect\w*|nasira|di gumana|hindi gumana|not working|stopped working|nag-?hang|leak\w*|punit|faulty|fake|peke)\b", re.I),
    "question_or_request": re.compile(r"\?|\b(?:pwede|paano|how to|anyone|please|pls|sana)\b", re.I),
    "emoji": re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2764]"),
    "elongation_or_caps": re.compile(r"([a-z])\1{3,}|[A-Z]{4,}"),
    "not_yet_used": re.compile(r"\b(?:not yet used|yet to|haven'?t (?:tried|used|tested)|di ko pa (?:nagagamit|nasusubukan|nasubukan|nagamit)|hindi ko pa (?:nagagamit|nasubukan)|will (?:update|review)|waiting for|wala pa|to be updated)\b", re.I),
}


def tags_of(r):
    t = r["text"]
    out = [k for k, rx in TAGS.items() if rx.search(t)]
    words = len(t.split())
    if words <= 3:
        out.append("very_short (3 words or fewer)")
    elif words <= 6:
        out.append("short (4 to 6 words)")
    if words >= 60:
        out.append("long (60 words or more)")
    if r["stars"]:
        if (r["stars"] >= 4 and r["label"] == "negative") or (r["stars"] <= 2 and r["label"] == "positive"):
            out.append("star_vs_label_contradiction")
        if r["stars"] == 3:
            out.append("three_star")
    out.append("language:" + metrics_x.lang_of(t))
    return out


def analyse(path):
    path = pathlib.Path(path)
    model, name = path.stem.split("__", 1)
    rows = {r["id"]: r for r in (xdata.load_firecs(name.split("_", 1)[1]) if name.startswith("firecs_") else xdata.load_marketplace()[name])}
    pred = [p for p in csv.DictReader(open(path, encoding="utf-8")) if rows[p["id"]]["conf"] in ("high", "published")]
    cells, prevalence, errors_by_tag, examples = {}, {}, {}, {}
    n_err = 0
    for p in pred:
        r = rows[p["id"]]
        tags = tags_of(r)
        wrong = p["pred"] != r["label"]
        for t in tags:
            prevalence[t] = prevalence.get(t, 0) + 1
            if wrong:
                errors_by_tag[t] = errors_by_tag.get(t, 0) + 1
        if wrong:
            n_err += 1
            cell = f"{r['label']}->{p['pred']}"
            cells[cell] = cells.get(cell, 0) + 1
            examples.setdefault(cell, [])
            if len(examples[cell]) < 6:
                examples[cell].append({"id": r["id"], "stars": r["stars"], "text": " ".join(r["text"].split())[:230], "tags": [t for t in tags if not t.startswith("language")]})
    table = {t: {"reviews": prevalence[t], "errors": errors_by_tag.get(t, 0), "error_rate": round(errors_by_tag.get(t, 0) / prevalence[t], 3)} for t in sorted(prevalence)}
    return {"model": model, "set": name, "scored": len(pred), "errors": n_err, "error_rate": round(n_err / len(pred), 3), "confusion_cells": dict(sorted(cells.items(), key=lambda kv: -kv[1])),
            "tags": table, "examples": examples}


if __name__ == "__main__":
    for path in sys.argv[1:]:
        out = analyse(path)
        json.dump(out, open(xdata.X / "results" / f"error_analysis__{out['model']}__{out['set']}.json", "w"), indent=1, ensure_ascii=False)
        print(out["set"], "errors", out["errors"], "of", out["scored"], out["confusion_cells"])
