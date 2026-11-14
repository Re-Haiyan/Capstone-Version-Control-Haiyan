"""Clause-level context: a contrast marker lets the next clause resolve a soft statement, never a genuine complaint.

The resolution of mild heat and plain thickness is OFF by default (the owner decides under the annotation policy);
the resolution of a feared fake is on. Both directions are tested.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import hazard_model, registry  # noqa: E402


def flags(model, text, product, stars=3):
    a = model.analyze_batch([text], [stars], listing={"name": product})[0]
    return set(a["review_tags"]) | set(a.get("review_extra_tags") or [])


class ClauseContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.pop(hazard_model.CLAUSE_ENV, None)
        cls.model = registry.load_model()

    def tearDown(self):
        os.environ.pop(hazard_model.CLAUSE_ENV, None)

    def enable(self, value="safety,quality"):
        os.environ[hazard_model.CLAUSE_ENV] = value

    # a feared fake resolved as genuine: on by default
    def test_a_feared_fake_that_is_genuine_is_not_counterfeit(self):
        self.assertNotIn("counterfeit", flags(self.model, "Akala ko peke pero original pala.", "Wireless Earbuds"))
        self.assertNotIn("counterfeit", flags(self.model, "I thought it was fake but it is original.", "Wireless Earbuds"))

    def test_a_real_fake_report_stays(self):
        self.assertIn("counterfeit", flags(self.model, "Peke ito, hindi original.", "Wireless Earbuds", 1))
        self.assertIn("counterfeit", flags(self.model, "Akala ko original pero peke pala.", "Wireless Earbuds", 1))

    # off by default
    def test_by_default_a_soft_statement_followed_by_okay_is_unchanged(self):
        self.assertIn("quality", flags(self.model, "Manipis pero okay naman.", "Bedsheet Set"))
        self.assertIn("safety", flags(self.model, "Mainit pero normal lang.", "Phone Charger 20W"))

    # on, by the switch
    def test_when_enabled_a_plain_description_with_a_benign_resolution_is_not_a_complaint(self):
        self.enable()
        self.assertNotIn("quality", flags(self.model, "Manipis pero okay naman.", "Bedsheet Set"))
        self.assertNotIn("safety", flags(self.model, "Mainit pero normal lang.", "Phone Charger 20W"))

    def test_when_enabled_an_intensified_or_judged_statement_is_still_a_complaint(self):
        self.enable()
        self.assertIn("quality", flags(self.model, "Sobrang manipis pero okay naman.", "Bedsheet Set"))
        self.assertIn("quality", flags(self.model, "Manipis, parang papel, pero okay lang.", "Bedsheet Set"))
        self.assertIn("safety", flags(self.model, "Sobrang init pero normal lang daw.", "Phone Charger 20W"))
        self.assertIn("safety", flags(self.model, "Mainit pero nakakatakot, baka masunog.", "Phone Charger 20W"))

    def test_a_complaint_in_the_clause_after_the_contrast_is_never_touched(self):
        self.enable()
        self.assertTrue({"defect", "quality"} & flags(self.model, "Maganda pero madaling masira.", "Backpack"))
        self.assertIn("not_as_described", flags(self.model, "Okay naman pero kulang ang laman.", "Shampoo 340ml"))

    def test_the_switch_ignores_unknown_values(self):
        self.enable("nonsense, ,defect")
        self.assertEqual(hazard_model._clause_flags(), frozenset())


if __name__ == "__main__":
    unittest.main()
