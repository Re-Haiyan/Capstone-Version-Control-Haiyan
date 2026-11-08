"""Focused regression cases for the shipped extra-label revision r8."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "sentiment-analysis"))

from defaketive_sentiment.extra_labels import (  # noqa: E402
    EXTRA_RULES_REVISION_08,
    not_as_described_spans,
)
from defaketive_sentiment import registry  # noqa: E402


class ExtraLabelRules(unittest.TestCase):
    def test_explicit_mismatches_are_labeled(self) -> None:
        cases = [
            "This is NOT a data cable.",
            "from the photo I thought I'd get different colors",
            "this does not charge at 140watts",
            "hindi ito fast charging",
            "the camera holder is not compatible to the tapo base on the promotion picture",
            "not authrntic JBL as seen on your ads",
            "brand iba sa lalagyanan",
            "sa picture dualshock 4 pag deliver sakin doubleshock 4",
            "this not mechanical keyboard",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertTrue(not_as_described_spans(text, EXTRA_RULES_REVISION_08))

    def test_neutral_charging_tier_is_not_a_label(self) -> None:
        model = registry.load_model()
        result = model.analyze("fast charging only no super fast charging")
        self.assertNotIn("defect", result["review_tags"])
        self.assertNotIn("not_as_described", result["review_extra_tags"])


if __name__ == "__main__":
    unittest.main()
