"""Compare the outputs of two checkouts produced by release_compare.py: behaviour change, API keys, scores against the labels.

    D:\defaketive-train\Scripts\python.exe research\release_diff.py old.json new.json
Writes research/results/release_behaviour_diff.json. Scores are against team-supplied labels of unverified provenance; the
'test' split is the historical benchmark (inspected during development), 'train' is development data.
"""
import collections, json, pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import FLAGS5, ROOT, load, prf

old = json.load(open(sys.argv[1]))["reviews"]; new = json.load(open(sys.argv[2]))["reviews"]
assert set(old) == set(new)
rows = {"train": load("train_v3"), "test": load("test_v3")}
out = {"reviews": len(old)}
flags_of = lambda d: set(d["tags"]) | set(d["extra"])
changed = [i for i in old if flags_of(old[i]) != flags_of(new[i])]
gained = collections.Counter(); lost = collections.Counter()
for i in changed:
    for f in flags_of(new[i]) - flags_of(old[i]): gained[f] += 1
    for f in flags_of(old[i]) - flags_of(new[i]): lost[f] += 1
out["reviews_with_changed_flags"] = len(changed); out["flags_gained"] = dict(gained); out["flags_lost"] = dict(lost)
out["sentiment_labels_changed"] = sum(1 for i in old if old[i]["label"] != new[i]["label"])
old_keys = set().union(*[set(d["keys"]) for d in old.values()]); new_keys = set().union(*[set(d["keys"]) for d in new.values()])
out["analysis_keys_removed"] = sorted(old_keys - new_keys); out["analysis_keys_added"] = sorted(new_keys - old_keys)
out["reviews_without_evidence_key_in_new"] = sum(1 for d in new.values() if not d["has_evidence_key"])
scores = {}
for split, rs in rows.items():
    Y = np.array([r["y"][:5] for r in rs]); ids = [r["id"] for r in rs]
    po = np.array([[1 if f in flags_of(old[i]) else 0 for f in FLAGS5] for i in ids]); pn = np.array([[1 if f in flags_of(new[i]) else 0 for f in FLAGS5] for i in ids])
    scores[split] = {f: {"old_f1": round(prf(Y[:, k], po[:, k])["f1"], 3), "new_f1": round(prf(Y[:, k], pn[:, k])["f1"], 3), "old_precision": round(prf(Y[:, k], po[:, k])["precision"], 3), "new_precision": round(prf(Y[:, k], pn[:, k])["precision"], 3),
                         "old_recall": round(prf(Y[:, k], po[:, k])["recall"], 3), "new_recall": round(prf(Y[:, k], pn[:, k])["recall"], 3)} for k, f in enumerate(FLAGS5)}
    gold_ids = {i for i in ids}
out["scores"] = scores
# examples of what changed, for review
ex = []
text = {r["id"]: r["text"] for rs in rows.values() for r in rs}; gold = {r["id"]: {f for f, v in zip(FLAGS5, r["y"][:5]) if v} for rs in rows.values() for r in rs}
for i in changed[:400]:
    ex.append({"id": i, "gained": sorted(flags_of(new[i]) - flags_of(old[i])), "lost": sorted(flags_of(old[i]) - flags_of(new[i])), "gold": sorted(gold[i]), "text": text[i][:110]})
out["changed_examples"] = ex
json.dump(out, open(ROOT / "research" / "results" / "release_behaviour_diff.json", "w"), indent=1, ensure_ascii=False)
print("reviews with changed flags:", len(changed), "of", len(old)); print("gained:", dict(gained)); print("lost:", dict(lost))
print("sentiment labels changed:", out["sentiment_labels_changed"], "| analysis keys removed:", out["analysis_keys_removed"], "| added:", out["analysis_keys_added"], "| new reviews missing the evidence key:", out["reviews_without_evidence_key_in_new"])
for split in ("train", "test"):
    print(split, {f: f"{v['old_f1']:.3f}->{v['new_f1']:.3f}" for f, v in scores[split].items()})
# of the changes, how many agree with the gold label (gained flags that are gold / lost flags that are not gold)
good = bad = 0
for e in ex:
    for f in e["gained"]: good += f in e["gold"]; bad += f not in e["gold"]
    for f in e["lost"]: good += f not in e["gold"]; bad += f in e["gold"]
print(f"of the first 400 changed reviews' individual flag changes: {good} agree with the supplied label, {bad} disagree")
