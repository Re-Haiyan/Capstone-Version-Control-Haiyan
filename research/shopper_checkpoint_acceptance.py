"""Report real pinned-checkpoint predictions for representative labeled examples.

These hand-written examples are regression probes, not a language benchmark.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend/sentiment-analysis"))
from defaketive_sentiment import registry

CASES = [
    ("English", "Excellent quality, works perfectly. I love it!", "positive"),
    ("English", "Terrible product. Broken and useless, a waste of money.", "negative"),
    ("English", "I have not tested it yet.", "neutral"),
    ("Filipino", "Napakaganda at matibay, sulit na sulit ang binayad ko!", "positive"),
    ("Filipino", "Pangit at sira agad. Sayang ang pera ko.", "negative"),
    ("Filipino", "Hindi ko pa nasusubukan.", "neutral"),
    ("Taglish", "Super ganda, works perfectly at sulit sa price!", "positive"),
    ("Taglish", "Broken agad after one day, sayang ang money.", "negative"),
    ("Taglish", "Not yet tested, hindi ko pa nagagamit.", "neutral"),
]

if __name__ == "__main__":
    model = registry.load_model()
    results = []
    for language, text, expected in CASES:
        result = model.analyze(text, listing={"name": "Power Bank"})
        results.append({"language": language, "text": text, "expected": expected,
                        "actual": result["sentiment"]["initial_label"],
                        "passed": result["sentiment"]["initial_label"] == expected})
    hazard_probes = []
    for text in (
        "Excellent charger, great quality, fast charging, very happy and highly recommended! The cable sparked once.",
        "Love this charger! Fast charging, beautiful design, excellent quality and great value. It burned my hand once.",
        "Maganda at sulit, mabilis mag charge, satisfied ako! Pero umusok ang charger.",
    ):
        result = model.analyze(text, 5, listing={"name": "Phone Charger"})
        hazard_probes.append({"text": text, "initial_label": result["sentiment"]["initial_label"],
                              "tags": result["review_tags"], "evidence": result["review_evidence"]})
    print(json.dumps({"model": model.sentiment.trained_classifier.manifest,
                      "results": results, "passed": sum(r["passed"] for r in results),
                      "hazard_probes": hazard_probes}, ensure_ascii=False, indent=2))
    sys.exit(0 if all(r["passed"] for r in results) else 1)
