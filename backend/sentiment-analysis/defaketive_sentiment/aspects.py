"""Conservative, explainable aspect cues; not a trained aspect classifier.

Evidence is an exact substring with Python character offsets. Unknown language,
questions and hypothetical clauses abstain. This layer never changes warnings
or the existing three-class sentiment model.
"""
import re

VERSION = "aspects-cues-1"
TOPICS = {
    "delivery": r"delivery|shipping|courier|rider|deliver|dumating|dating",
    "packaging": r"packaging|package|packed|balot|pagkabalot|box|kahon|bubble wrap",
    "seller_service": r"seller|service|refund|reply|respond|responsive|accommodating",
    "price": r"price|presyo|mura|mahal|sulit|affordable|expensive|value for money|worth",
    "quality": r"quality|kalidad|durable|durability|flimsy|matibay|manipis|build|material",
    "functionality": r"working|work|works|gumagana|gumana|nagana|functionality|performance|charge|charging|battery|earbud|earphone|sound|audio|screen|sira|defective",
}
TOPICS = {key: re.compile(rf"\b(?:{value})\b", re.I) for key, value in TOPICS.items()}
POSITIVE = re.compile(r"\b(?:good|great|excellent|nice|fast|quick|mabilis|maayos|maganda|matibay|durable|sulit|mura|affordable|responsive|accommodating|working|works|gumagana|gumana|nagana|worth it)\b", re.I)
NEGATIVE = re.compile(r"\b(?:bad|poor|terrible|slow|mabagal|sira|defective|broken|flimsy|pangit|expensive|mahal|damaged|basag|late|useless|disappointing)\b", re.I)
NEGATOR = re.compile(r"\b(?:not|no|never|hindi|di|wala|walang|isn't|isnt|doesn't|doesnt|don't|dont|won't|wont)\s+(?:(?:po|naman|sya|siya|ito|that|very|so|really|even|na|pa)\s+){0,3}$", re.I)
FAILURE = re.compile(r"\b(?:(?:only one|isa(?:ng)?\s+(?:\w+\s+)?lang)\s+(?:\w+\s+){0,3}(?:working|works|gumagana|gumana|nagana)|(?:does not|cannot|can't|won't|doesn't)\s+(?:work|charge|respond))\b", re.I)
HYPOTHETICAL = re.compile(r"\b(?:sana|hope|hopefully|baka|maybe|wish|if|kung|akala|thought)\b", re.I)
SPLIT = re.compile(r"[.!?;,\n]+|\b(?:but|pero|kaso|however|and|at)\b", re.I)


def analyze_aspects(text):
    raw = str(text or "")
    evidence = []
    start = 0
    boundaries = [(m.start(), m.end()) for m in SPLIT.finditer(raw)] + [(len(raw), len(raw))]
    for stop, next_start in boundaries:
        clause = raw[start:stop]
        left = start + len(clause) - len(clause.lstrip())
        clause = clause.strip()
        end = left + len(clause)
        start = next_start
        if not clause or HYPOTHETICAL.search(clause) or raw[stop:next_start].startswith("?"):
            continue
        topics = [key for key, pattern in TOPICS.items() if pattern.search(clause)]
        # Do not assign a shared polarity to two competing topics.
        if len(topics) != 1:
            continue
        polarities = set()
        for pattern, label in ((POSITIVE, "positive"), (NEGATIVE, "negative")):
            for match in pattern.finditer(clause):
                negated = NEGATOR.search(clause[:match.start()])
                if negated:
                    if label == "positive":
                        polarities.add("negative")
                    # Absence of a problem isn't automatically praise.
                else:
                    polarities.add(label)
        if FAILURE.search(clause):
            polarities = {"negative"}
        if not polarities:
            continue
        label = "mixed" if len(polarities) > 1 else next(iter(polarities))
        evidence.append({"aspect": topics[0], "label": label, "text": clause,
                         "span": [left, end], "method": VERSION})
    labels = {item["label"] for item in evidence}
    mixed = "mixed" in labels or {"positive", "negative"} <= labels
    return {"version": VERSION, "status": "experimental", "evidence": evidence,
            "mixed_evidence": mixed}
