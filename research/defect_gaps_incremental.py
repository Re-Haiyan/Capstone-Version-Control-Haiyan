"""Product-level effect of a rule change WITHOUT re-running the model on every review.

The saved production analyses (one per review) are the baseline. Only the model call inside the production analysis is replaced:

    incremental   a review whose text no changed rule can touch gets its saved analysis back; every other review is re-analysed by
                  the checkout's real model. The production aggregation (analyze_product_json: sampling weights, rates, verdict) then
                  runs unchanged on top, so the product-level numbers come from the normal code path.
    cached        every review comes from the saved analyses (nothing is re-analysed): proves the aggregation reproduces the stored
                  production summaries exactly, i.e. that the baseline side of the comparison is the production result.
    full          nothing is reused: every review is re-analysed (the slow reference used to verify `incremental`).

"Cannot be touched" is decided by a deliberately wide text filter (AFFECTED below): wide on purpose, because a review wrongly
treated as affected only costs time, while one wrongly treated as unaffected would hide a change. The filter is checked, not
trusted: `full` mode on several products (one with thousands of reviews) must give byte-identical results to `incremental`.

    python defect_gaps_incremental.py --root D:\\cvc-review --prod prod_full.jsonl.gz --mode incremental --out cand.json
    (--only substrings of product links, --dump DIR writes the complete result of those products for an exact comparison)
Nothing is written to any database; the production file is only read.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import multiprocessing as mp
import os
import pathlib
import re
import sys

# Text that can reach a changed rule. Changed code: (1) the drain exemption row and its cue window, the negated-drain row, the
# abrupt cues ("isang gamit", number + minutes), (2) the two charging-failure keyword rules, (3) the "nothing was damaged" denial
# (a negator + up to two words + a damage word). Each is covered by a looser test than the rule itself, on the raw text and on the text
# with repeated letters collapsed (the checker normalises spelling, so "lowbaaat" reaches the rules as "lowbat").
_DRAIN = re.compile(r"l[o0]w?\s?-?\s?b[a@]t|lobat|batt?er|baterya|ubos|drain|discharg|nauubus|maubos|power\s?bank", re.I)
_CHARGE = re.compile(r"char?g|chrg|chach|cha-?\s?cha", re.I)
_DAMAGE = re.compile(r"damag|dent|broke|basag|sira|yupi|leak|tagas|crack|punit|butas", re.I)
_NEGATOR = re.compile(r"\bnot\b|n't|n’t|\bno\b|never|without|walang|wala|hindi|hinde|\bdi\b|\bd\b|hnd|hnde|withot|withoy", re.I)


def affected(text: str) -> bool:
    for s in (text, re.sub(r"(.)\1+", r"\1", text.lower())):
        if _DRAIN.search(s) or _CHARGE.search(s) or (_DAMAGE.search(s) and _NEGATOR.search(s)):
            return True
    return False


_S: dict = {}


def _init(root: str, mode: str) -> None:
    backend = os.path.join(root, "backend")
    sys.path.insert(0, backend)
    sys.path.insert(0, os.path.join(backend, "sentiment-analysis"))
    os.chdir(backend)
    os.environ.setdefault("DEFAKETIVE_SECRET_KEY", "impact-only")
    import dashboard_utils as du
    from defaketive_sentiment import analyze_reviews as ar
    from defaketive_sentiment.registry import load_model

    _S.update(du=du, ar=ar, model=load_model(), mode=mode, orig=ar._analyze_all)


def _diff_keys(a: dict, b: dict) -> list[str]:
    return sorted(k for k in set(a) | set(b) if json.dumps(a.get(k), sort_keys=True, default=str) != json.dumps(b.get(k), sort_keys=True, default=str))


def _make_patch(cache: dict, mode: str, stats: dict):
    orig = _S["orig"]

    def patched(model, texts, ratings, listing=None):
        out = [None] * len(texts)
        todo = []
        for i, (t, r) in enumerate(zip(texts, ratings)):
            hit = cache.get((t, str(r)))
            if hit is not None and (mode == "cached" or not affected(t)):
                out[i] = copy.deepcopy(hit)
            else:
                todo.append(i)
        if todo:
            fresh = orig(model, [texts[i] for i in todo], [ratings[i] for i in todo], listing=listing)
            for i, a in zip(todo, fresh):
                out[i] = a
                old = cache.get((texts[i], str(ratings[i])))
                if old is not None:
                    d = _diff_keys(old, a)
                    stats["recomputed_with_saved"] += 1
                    if d:
                        stats["changed"].append({"text": texts[i][:160], "keys": d,
                                                 "defect_before": "defect" in (old.get("review_tags") or []), "defect_after": "defect" in (a.get("review_tags") or []),
                                                 "safety_same": (old.get("review_tags") or []).count("safety") == (a.get("review_tags") or []).count("safety"),
                                                 "label_same": old.get("label") == a.get("label")})
                else:
                    stats["recomputed_no_saved"] += 1
        stats["reused"] += len(texts) - len(todo)
        return out

    return patched


def _one(item):
    link, raw, dump = item["link"], item["raw"], item["dump"]
    ar, du, mode = _S["ar"], _S["du"], _S["mode"]
    product = copy.deepcopy(raw)
    cache = {}
    for c in product.get("comments") or []:
        a = c.get("sentiment_analysis") if isinstance(c, dict) else None
        if a:
            cache[(ar._review_text(c), str(c.get("rating")))] = a
    stats = {"reused": 0, "recomputed_with_saved": 0, "recomputed_no_saved": 0, "changed": []}
    if mode == "full":
        ar._analyze_all = _S["orig"]
        for c in product.get("comments") or []:
            if isinstance(c, dict):
                c.pop("sentiment_analysis", None)
    else:
        ar._analyze_all = _make_patch(cache, mode, stats)
    result = ar.analyze_product_json([product], _S["model"])[0]
    view = du.badge_view(result)
    summ = result.get("sentiment_summary") or {}
    flags = {**(summ.get("flags") or {}), **(summ.get("reports") or {})}
    tags = {"defect": [], "safety": []}
    for i, c in enumerate(result.get("comments") or []):
        t = set(((c.get("sentiment_analysis") or {}).get("review_tags")) or [])
        for k in tags:
            if k in t:
                tags[k].append(i)
    blob = json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
    stored_summary = json.dumps(raw.get("sentiment_summary"), sort_keys=True, default=str)
    rec = {
        "link": link, "name": " ".join(str(result.get("name") or "")[:80].split()), "reviews": len(result.get("comments") or []),
        "state": view["state"], "tone": view["tone"], "headline": view["headline"], "usable": summ.get("usable_review_count"),
        "safety_flagged": (summ.get("safety") or {}).get("flagged_reviews"), "safety_tier": (summ.get("safety") or {}).get("tier"),
        "flag_counts": {k: (v or {}).get("flagged_reviews") for k, v in flags.items()},
        "defect_state": (flags.get("defect") or {}).get("state"), "defect_rate": (flags.get("defect") or {}).get("rate"),
        "defect_rate_lb": (flags.get("defect") or {}).get("rate_lower_bound"), "tags": tags,
        "result_sha": hashlib.sha256(blob.encode()).hexdigest()[:16],
        "summary_equals_stored": json.dumps(summ, sort_keys=True, default=str) == stored_summary,
        "reused": stats["reused"], "recomputed": stats["recomputed_with_saved"] + stats["recomputed_no_saved"],
        "recomputed_no_saved": stats["recomputed_no_saved"], "changed_reviews": stats["changed"],
        # exactly what the app's recommendation reads
        "rec_input": {"badge_view": {k: view.get(k) for k in ("available", "state", "tone", "reviews_analyzed", "counts")} | {"badges": [{"category": b["category"], "mentions": b["mentions"]} for b in view.get("badges") or []]},
                      "sentiment_summary": {"sentiment_counts": summ.get("sentiment_counts"), "sentiment_shares": summ.get("sentiment_shares")}, "checked_with_current": True},
    }
    if dump:
        pathlib.Path(dump).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(dump) / (hashlib.md5(link.encode()).hexdigest()[:12] + ".json")).write_text(blob, encoding="utf-8")
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True)
    ap.add_argument("--prod", required=True, help="prod_full.jsonl.gz: {link, source, raw} lines, raw = the product exactly as stored")
    ap.add_argument("--mode", choices=("incremental", "cached", "full"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--only", help="comma separated substrings of the product link")
    ap.add_argument("--dump", help="directory: write each product's complete result there (exact comparison)")
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")
    items = [{**json.loads(line), "dump": args.dump} for line in gzip.open(args.prod, "rt", encoding="utf-8")]
    if args.only:
        keys = args.only.split(",")
        items = [i for i in items if any(k in i["link"] for k in keys)]
    items.sort(key=lambda i: -len(i["raw"].get("comments") or []))
    rows = []
    with mp.Pool(args.workers, initializer=_init, initargs=(args.root, args.mode)) as pool:
        for n, r in enumerate(pool.imap_unordered(_one, items, chunksize=1), 1):
            rows.append(r)
            if n % 50 == 0:
                print(n, "of", len(items), flush=True)
    json.dump({"root": args.root, "mode": args.mode, "products": rows}, open(args.out, "w", encoding="utf-8"), ensure_ascii=False)
    tot = sum(r["reviews"] for r in rows)
    print(f"{len(rows)} products, {tot} reviews: reused {sum(r['reused'] for r in rows)}, re-analysed {sum(r['recomputed'] for r in rows)}")


if __name__ == "__main__":
    main()
