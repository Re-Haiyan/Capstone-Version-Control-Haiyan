"""Fixed training / validation splits for the fine-tuning experiments (writes data/splits.json; deterministic).

    FiReCS validation: 10% of FiReCS train, stratified by label, one text never on both sides (grouped by normalised text).
    Marketplace validation: 12% of the PRODUCTS of train_v3 (a product is wholly on one side); high-confidence rows, texts deduplicated
    by (product, normalised text). market_test_v3 (historical benchmark) and FiReCS test are never read here.
"""
import json, pathlib, random, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata  # noqa: E402


def build():
    rng = random.Random(13)
    fc = xdata.load_firecs("train")
    by_text = {}
    for r in fc:
        by_text.setdefault(xdata.norm_text(r["text"]), []).append(r)
    firecs_val_ids, firecs_train_ids = [], []
    for label in xdata.LABELS:
        keys = sorted(k for k, v in by_text.items() if v[0]["label"] == label)
        rng.shuffle(keys)
        cut = int(len(keys) * 0.10)
        for i, k in enumerate(keys):
            (firecs_val_ids if i < cut else firecs_train_ids).extend(r["id"] for r in by_text[k])
    mk = [r for r in xdata.load_marketplace()["market_train_v3"] if r["conf"] == "high"]
    seen, uniq = set(), []
    for r in mk:
        k = (r["product"], xdata.norm_text(r["text"]))
        if k not in seen:
            seen.add(k); uniq.append(r)
    products = sorted({r["product"] for r in uniq})
    rng.shuffle(products)
    val_products = set(products[: int(len(products) * 0.12)])
    out = {"firecs_train": firecs_train_ids, "firecs_val": firecs_val_ids,
           "market_train": [r["id"] for r in uniq if r["product"] not in val_products], "market_val": [r["id"] for r in uniq if r["product"] in val_products],
           "market_val_products": len(val_products), "market_train_products": len(products) - len(val_products),
           "market_rows_before_dedup": len(mk), "market_rows_after_dedup": len(uniq)}
    json.dump(out, open(xdata.DATA / "splits.json", "w"))
    return out


if __name__ == "__main__":
    s = build()
    print({k: (len(v) if isinstance(v, list) else v) for k, v in s.items()})
