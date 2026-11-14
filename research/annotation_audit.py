"""Build the annotation adjudication queue from the labelled TRAINING file (and report counts for the historical test).

    D:\\defaketive-train\\Scripts\\python.exe research\\annotation_audit.py

Checks use the human labels and plain word lists only; no model output. Every row is a SUSPICION for a human to
adjudicate. Nothing is relabelled. Writes research/annotation_audit.md and research/annotation_audit_queue.csv.
"""
import collections, csv, pathlib, re, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import FLAGS6, ROOT, load

train = load("train_v3")
G = lambda r: {f for f, v in zip(FLAGS6, r["y"]) if v}
queue = []


def add(r, issue, reason, proposal, needs_listing, priority):
    queue.append({"id": r["id"], "product": r["product"][:60], "review_text": r["text"].replace("\n", " ")[:300], "stars": r["stars"],
                  "current_labels": ";".join(sorted(G(r))) or "none", "suspected_inconsistency": issue, "reason": reason,
                  "proposed_interpretation_unverified": proposal, "needs_listing_context": needs_listing, "priority": priority})


HAZ = re.compile(r"umusok|usok|smok|sunog|nasunog|masunog|sumabog|pumutok|sparks?|nag-?spark|short circuit|nakuryente|kuryente|burn(?:ed|t)|nagkasugat|sugat|pantal|rash|nag-?allerg|allergy|namaga|namumula|nagtae|nagsuka|vomit|diarrh|nabilaukan|choke|expired|panis|amag|uod|hinihingal|nahilo|nakakahilo|bloat", re.I)
HAZ_FEAR = re.compile(r"nakakatakot|delikado|dangerous|baka sumabog|baka masunog|nangamoy sunog|amoy sunog|burning smell", re.I)
COMPLAINT = re.compile(r"hindi (?:gumana|gumagana|umandar|nag-?on)|di (?:gumana|gumagana)|not working|doesn.t work|stopped working|sira|basag|broken|defect|peke|fake|mali ang|wrong|kulang|missing|pangit|poor quality|bad quality", re.I)
PRAISE = re.compile(r"maganda|ganda|bagay|sulit|worth|love|recommend|galing|satisfied|great|good|nice|perfect|thank", re.I)
DMG = re.compile(r"yupi|nayupi|dent|damag|crush|crumpl|butas|punit|basag|broken|leak|tagas|natapon", re.I)
PKG = re.compile(r"box|kahon|packag|packing|parcel|pouch|plastic|balot|bubble ?wrap|wrapper|carton|sachet", re.I)

for r in train:
    g, text = G(r), r["text"]
    # 1 hazard report labelled none / without safety
    if HAZ.search(text) and "safety" not in g and re.search(r"\b(?:ko|namin|ang akin|my|we|nag|naging|naka|nang|habang)\b", text, re.I) and not re.search(r"\b(?:no|walang|wala|hindi|di|not)\s+(?:\w+\s+){0,2}(?:rash|usok|smoke|burn|sunog|allerg)", text, re.I):
        word = HAZ.search(text).group(0).lower()
        strong = re.search(r"usok|smok|sunog|sumabog|pumutok|spark|short circuit|kuryente|burn", word)
        skin_food = re.search(r"rash|pantal|allerg|namaga|namumula|sugat|nagtae|nagsuka|vomit|diarrh|expired|panis|amag|uod|bloat|nabilaukan|choke", word)
        add(r, "hazard word, no safety label", "contains a hazard word (" + word + ") with a first-person cue but is not labelled safety", "safety if the product itself caused it; none if the word is about weather, food taste, or someone else", "no", 3 if (strong or HAZ_FEAR.search(text)) else (2 if skin_food else 1))
    # 2 fear of fire / explosion without safety
    if HAZ_FEAR.search(text) and "safety" not in g:
        add(r, "fear or danger wording, no safety label", "text says it is dangerous or smells burning (" + HAZ_FEAR.search(text).group(0) + ")", "policy question: is a stated fear of fire a safety report? The guide says 'umiinit habang nagchacharge, nakakatakot' is", "no", 3)
    # 3 praise review with defect/quality flagged
    if r["stars"] >= 4 and r["sentiment"] == "positive" and g & {"defect", "quality"} and not COMPLAINT.search(text) and PRAISE.search(text):
        add(r, "positive review marked as a product complaint", "5-star positive wording with " + "/".join(sorted(g & {"defect", "quality"})) + " and no complaint words", "none, unless the reviewer mentions a real fault in a part I could not see", "no", 2)
    # 4 negative with real complaint words and no flag
    if r["stars"] <= 2 and g == set() and COMPLAINT.search(text) and not re.search(r"seller|rider|delivery|courier|shipping", text, re.I):
        add(r, "negative review with complaint words, no label", "low rating and the words '" + COMPLAINT.search(text).group(0) + "', but labelled none", "defect, not_as_described or counterfeit depending on the word", "maybe", 2)
    # 5 damage + packing: defect vs delivery
    if DMG.search(text) and PKG.search(text):
        if "defect" in g and "delivery" not in g:
            add(r, "packing damage labelled defect without delivery", "damage and packing words together, labelled defect only", "delivery if only the box is damaged; defect if the item is", "no", 2)
        if "delivery" in g and "defect" not in g and re.search(r"(?:item|product|unit|laman|nakuha)\s+(?:is\s+|was\s+)?(?:damaged|broken|sira|basag|dented)|damage ang nakuha", text, re.I):
            add(r, "item damage labelled delivery only", "text says the item itself is damaged, labelled delivery only", "defect + delivery", "no", 2)
    # 6 listing-dependent mismatch wording
    if re.search(r"kalahati|half[- ]empty|freebies?|free gift|free shirt", text, re.I):
        add(r, "mismatch wording that depends on the listing", "half-empty or freebie wording; labelled " + (";".join(sorted(g)) or "none"), "not_as_described only if the listing promised the amount or the freebie", "yes", 1)
    if re.search(r"too (?:small|big|tight|loose)|masyadong (?:maliit|malaki|sikip)|sobrang (?:liit|sikip)", text, re.I):
        add(r, "fit complaint vs listing size", "'too small/big' wording; labelled " + (";".join(sorted(g)) or "none"), "not_as_described only if the size differs from the listing; otherwise a fit remark (usually none)", "yes", 1)
    if re.search(r"low ?bat|lobat|mabilis (?:ma)?(?:ubos|maubos)|drain", text, re.I):
        add(r, "battery drain label policy", "fast battery drain; labelled " + (";".join(sorted(g)) or "none"), "decide once: defect, quality or none (current labels are mostly none)", "no", 1)

# 7 near-duplicate label disagreement
vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)
X = vec.fit_transform([re.sub(r"\W+", " ", r["text"].casefold()) for r in train])
S = (X @ X.T).tocsr(); seen = set()
for i in range(S.shape[0]):
    row = S.getrow(i)
    for j, v in zip(row.indices, row.data):
        if j > i and v >= 0.85 and G(train[i]) != G(train[j]) and (i, j) not in seen:
            seen.add((i, j))
            for a, b in ((train[i], train[j]), (train[j], train[i])):
                add(a, "near-duplicate text with different labels", f"cosine {v:.2f} with {b['id']} which is labelled {';'.join(sorted(G(b))) or 'none'}", "adjudicate the pair together", "no", 3)

best = {}
for q in queue:
    k = (q["id"], q["suspected_inconsistency"])
    best.setdefault(k, q)
rows = sorted(best.values(), key=lambda q: (-q["priority"], q["suspected_inconsistency"], q["id"]))
out = ROOT / "research"
with open(out / "annotation_audit_queue.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
counts = collections.Counter(q["suspected_inconsistency"] for q in rows)
md = ["# Annotation audit: review queue for human adjudication", "",
      "Generated by `research/annotation_audit.py` from the labelled **training** file (3,946 high-confidence rows). "
      "These are **suspicions, not corrections**: each row names a possible inconsistency and a *proposed, unverified* reading. "
      "No label was changed. Full queue: `research/annotation_audit_queue.csv`.", "",
      "## Counts by suspected inconsistency", "", "| Suspected inconsistency | Rows |", "|---|---:|"]
md += [f"| {k} | {v} |" for k, v in counts.most_common()]
md += ["", f"Total distinct queue rows: {len({q['id'] for q in rows})} of {len(train)} training rows.", "",
       "Exact-text duplicates with conflicting labels: 0 (see `research/data_audit.json`). Near-duplicate pairs (cosine >= 0.85) with different labels are listed under the near-duplicate heading.", "",
       "## Highest-priority rows (priority 3 first; the first 80)", "",
       "| ID | Product | Review | Labels | Suspected inconsistency | Reason | Proposed (unverified) | Needs listing | Prio |", "|---|---|---|---|---|---|---|---|---:|"]
clean = lambda s: s.replace("|", "/")
for q in rows[:80]:
    md.append(f"| {q['id']} | {clean(q['product'][:30])} | {clean(q['review_text'][:140])} | {q['current_labels']} | {q['suspected_inconsistency']} | {clean(q['reason'][:90])} | {clean(q['proposed_interpretation_unverified'][:90])} | {q['needs_listing_context']} | {q['priority']} |")
md += ["", "## How to use this", "", "1. Open the CSV, sort by `priority`, and adjudicate the rows that matter for the five flags.",
       "2. Record the decision in a new column; keep the original label.", "3. Where the decision depends on the listing (`needs_listing_context` = yes), check the listing before deciding.",
       "4. Decisions that repeat across many rows belong in the policy (`research/annotation_policy_proposal.md`), not in row-by-row edits."]
open(out / "annotation_audit.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
print(len(rows), "queue rows;", dict(counts))
