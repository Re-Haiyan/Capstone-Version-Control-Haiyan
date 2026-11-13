"""Rules s5 (safety_lookalikes): fire, melting, swelling and misspelt short circuits are found;
a grounded plug and "kanina" are not read as a shock or burnt rice."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "sentiment-analysis"))

from defaketive_sentiment.hazard_model import LexiconHazardTagger  # noqa: E402

SAFETY_REPORTS = [
    "kaso nag cause sya nang shrt circuit.",
    "but the CHARGER YOU GAVE ME ITS DEFECTIVE IT IGNITES A FIRE SUDDENLY THE WIRE MELTS THANK GOD NO ONE HURTS",
    "MAKE SURE THE CHARGER THAT YOU WILL INCLUDE ITS NOT DEFECTIVE OR IT WILL CAUSE FIRE",
    "battery swollen.wrong color.",
    "The batteries are no longer original and one was bloated.",
    "I also bought a fast charging cable from them and it also melted and stopped working.",
    "nag amoy sunog siya kanina nung nagsaksak pa ako ng isang extension.",
    "I got grounded after touching my cord",
    "yung charger nagliyab",
]
NOT_SAFETY = [
    "grounded po ang cord pero maganda naman",
    "Grounded yung lightning pin ng powerbank. Pag sinaksak sa phone konting galaw nawawala agad sa charge",
    "Ang amazing dito ay ang Rapid fire button.",
    "I love the turbo fire button, it's like a built in auto clicker",
    "Fire HD tablet works great",
    "it doesn't melt even when hot, no sign of burned",
    "The wire won't melt, good quality",
    "lasang sunog na kanin",
    "ice cream melts fast but the cable is fine",
    "my body feels bloated after dinner, the scale is accurate",
]


def tagger() -> LexiconHazardTagger:
    return LexiconHazardTagger(rules="0.4", counterfeit_rules="c2")


class SafetyS5Tests(unittest.TestCase):
    def test_reports_are_flagged(self) -> None:
        for text in SAFETY_REPORTS:
            with self.subTest(text=text):
                result = tagger().tag_sentence(text)
                self.assertIn("safety", result["tags"], result.get("suppressed"))

    def test_look_alikes_are_not_flagged(self) -> None:
        for text in NOT_SAFETY:
            with self.subTest(text=text):
                self.assertNotIn("safety", tagger().tag_sentence(text)["tags"])


if __name__ == "__main__":
    unittest.main()
