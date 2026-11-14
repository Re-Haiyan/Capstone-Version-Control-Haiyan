"""What the proposed v2 policy would change: label statistics on the TRAINING file and the current rules' behaviour on probes.

    backend\\.venv\\Scripts\\python.exe research\\policy_impact.py

(1) Battery wording split into the five kinds the v2 proposal separates, with the team-supplied label distribution of each.
(2) Product-effect complaints (the proposed `effectiveness` flag): how many, and where the labels put them.
(3) Hypothetical fear of fire versus fear with a stated abnormal condition.
(4) What the current rules do on a fixed list of probe sentences, one group per v2 decision (A to J).
Nothing here changes a label or a rule. The historical test file is not read.
"""
import collections, csv, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality", "delivery")
rows = [r for r in csv.DictReader(open(ROOT / "evaluation/annotated/train_v3.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high"]
gold = lambda r: {f for f in r["flags"].replace(" ", "").split(";") if f in FLAGS}


def table(selected):
    c = collections.Counter(f for r in selected for f in (gold(r) or {"none"}))
    return {"rows": len(selected), "labels": dict(c.most_common())}


# 1. battery, five kinds (checked in this order; a review takes its most specific kind)
KINDS = [
    ("charging failure", re.compile(r"(?:hindi|di|ayaw|not|doesn.?t|won.?t|can.?t|cannot|d(?:i)?\s+na)\s+(?:\w+\s+){0,3}(?:mag-?charge|nagcha-?charge|na-?charge|charging|charge)|not charging|hindi nagcha-?charge|ayaw mag-?charge", re.I)),
    ("no longer holds a charge", re.compile(r"(?:hindi|di|d)\s+(?:na\s+)?(?:\w+\s+){0,2}(?:nag-?hold|tumatagal|humahawak)|doesn.?t hold|won.?t hold|nauubos agad|namamatay agad|biglang namamatay|dies (?:fast|quickly|suddenly)|bloat|namaga", re.I)),
    ("abnormally rapid discharge", re.compile(r"(?:\d+\s*%[^.]{0,30}\d+\s*(?:minutes?|mins?|min|oras|hours?|hrs?))|(?:wala pang|less than|sa loob ng|within)\s+\d+\s*(?:minutes?|mins?|min|hours?|hrs?)[^.]{0,30}(?:lowbat|lobat|ubos|drain|dead|empty)|(?:from|mula)\s+\d+\s*%?\s+(?:to|hanggang)\s+\d+", re.I)),
    ("subjective dissatisfaction", re.compile(r"(?:mabilis|madaling|madali)\s+(?:\w+\s+){0,2}(?:ma-?)?(?:low\s?bat\w*|lobat\w*|maubos|mawala|ubos|drain)|battery\s+(?:life\s+)?(?:is\s+)?(?:short|weak|poor|bad|mahina|maikli)|short battery|(?:ma)?low\s?bat\w*", re.I)),
    ("normal consumption / praise", re.compile(r"(?:tumatagal|matagal|long[- ]lasting|lasts? (?:long|all day))\s+(?:\w+\s+){0,3}battery|battery\s+(?:\w+\s+){0,3}(?:tumatagal|matagal|long|lasts|okay|ok|good|maganda)|(?:tipid|matipid)\s+(?:sa\s+)?battery", re.I)),
]
battery_re = re.compile(r"battery|low\s?bat|lobat|charg", re.I)
battery_rows = [r for r in rows if battery_re.search(r["review_text"])]
by_kind = collections.defaultdict(list)
for r in battery_rows:
    for name, rx in KINDS:
        if rx.search(r["review_text"]):
            by_kind[name].append(r); break
    else:
        by_kind["other battery or charging mention"].append(r)
battery = {name: table(sel) for name, sel in by_kind.items()}

# 2. effect complaints
EFFECT = re.compile(r"(?:hindi|di|walang|wala)\s+(?:\w+\s+){0,2}(?:umepekto|epekto|tumalab|effective|nakatulong|nagwork|bumula|bumubula|bomubola|pumuti|nag-?whiten)|no\s+(?:effect|results?|difference)|not\s+(?:effective|working for me)|didn.?t\s+(?:work for me|help|whiten|lighten)|hindi\s+gumana\s+sa(?:kin| akin)|walang nangyari", re.I)
effect_rows = [r for r in rows if EFFECT.search(r["review_text"])]
effect = table(effect_rows)
effect["where_the_flags_land"] = "see labels"
effect["by_group"] = dict(collections.Counter(next((k.get("group", "") for k in []), "") for _ in []))
key = {r["id"]: r for r in csv.DictReader(open(ROOT / "evaluation/annotated/train_v3_key.csv", encoding="utf-8-sig"))}
effect["by_group"] = dict(collections.Counter(key.get(r["id"], {}).get("group", "?") for r in effect_rows).most_common())
effect["examples"] = [r["review_text"][:110] for r in effect_rows[:6]]

# 3. fear of fire
FEAR = re.compile(r"baka\s+(?:sumabog|masunog|magka-?sunog|umusok)|natatakot|nakakatakot|worried|afraid|delikado|dangerous|scared", re.I)
ABNORMAL = re.compile(r"umusok|usok|smok|sunog\b|nasunog|amoy sunog|burning smell|spark|nag-?spark|kuryente|shock|sobrang init|init na init|bumuga|namaga|bloat|sumabog na|pumutok|melt|natunaw|(?:uminit|umiinit|mainit)\s+(?:\w+\s+){0,3}(?:habang|kahit|agad|kaagad|sobra)", re.I)
fear_rows = [r for r in rows if FEAR.search(r["review_text"])]
hypo = [r for r in fear_rows if not ABNORMAL.search(r["review_text"])]
withc = [r for r in fear_rows if ABNORMAL.search(r["review_text"])]
fear = {"fear wording, no stated abnormal condition (hypothetical)": table(hypo), "fear wording with a stated abnormal condition": table(withc)}

# 4. what the current rules do on probes
from defaketive_sentiment import registry  # noqa: E402
model = registry.load_model()
PROBES = {
    "A packaging damage": [("Yupi yupi ang box pero okay ang item", "Rice Cooker 1.8L"), ("Yupi ang box at basag ang takip ng rice cooker", "Rice Cooker 1.8L"), ("Late dumating at basang basa ang kahon", "Shampoo 340ml")],
    "B battery": [("Mabilis malowbat", "Handheld Fan"), ("Hindi na nagcha-charge, ayaw na mag-on", "Handheld Fan"), ("From 100% to 20% in 10 minutes lang", "Power Bank 10000mAh"), ("Hindi na nag-hold ng charge pagkatapos ng isang linggo", "Wireless Earbuds")],
    "C size": [("Masyadong maliit sa akin, medium ako", "Dress for Women"), ("Large ang inorder ko pero small ang dumating", "Dress for Women"), ("Size 42 ang order ko, 43 ang pinadala", "Running Shoes")],
    "D freebies": [("Walang freebie na kasama", "Shampoo 340ml"), ("Nakalagay sa listing may free tumbler pero wala", "Protein Powder 1lb")],
    "E half-empty": [("Kalahati lang ang laman ng pack", "Shampoo 340ml"), ("Buy 1 take 1 pero tig kalahati lang ang laman", "Shampoo 340ml"), ("Tumagas at kalahati na lang ang laman", "Lotion 200ml")],
    "F fear of fire": [("Baka sumabog yung charger", "Phone Charger 20W"), ("Umiinit habang nagchacharge, nakakatakot", "Phone Charger 20W"), ("Umusok na at nakakatakot", "Phone Charger 20W")],
    "G thin": [("Manipis pero okay naman", "Bedsheet Set"), ("Sobrang manipis, parang papel", "Bedsheet Set"), ("Manipis pero pwede na", "Bedsheet Set")],
    "H safety+defect": [("Umusok at hindi na gumana", "Phone Charger 20W"), ("Umusok ang charger", "Phone Charger 20W")],
    "I counterfeit+defect": [("Peke at sira agad", "Wireless Earbuds"), ("Peke ito", "Wireless Earbuds")],
    "J effectiveness": [("Hindi umepekto sa akin ang serum", "Whitening Serum"), ("Walang epekto, hindi pumuti", "Whitening Serum")],
}
probes = {}
for group, items in PROBES.items():
    probes[group] = []
    for text, product in items:
        a = model.analyze_batch([text], [3], listing={"name": product})[0]
        probes[group].append({"text": text, "product": product, "flags": sorted(set(a["review_tags"]) | set(a.get("review_extra_tags") or []))})
out = {"training_rows": len(rows), "battery_kinds": battery, "effect_complaints": effect, "fear_of_fire": fear, "probes_current_rules": probes}
json.dump(out, open(ROOT / "research" / "results" / "policy_impact.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("BATTERY KINDS"); [print(f"  {k:40} rows {v['rows']:4}  {v['labels']}") for k, v in battery.items()]
print("EFFECT COMPLAINTS", effect["rows"], effect["labels"], effect["by_group"])
print("FEAR", {k: (v["rows"], v["labels"]) for k, v in fear.items()})
for g, items in probes.items():
    print(g); [print("   ", i["flags"], "|", i["text"]) for i in items]
