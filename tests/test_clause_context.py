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


class OrderAndArrivalAcrossAContrast(unittest.TestCase):
    """The splitter cuts at "pero"; an order clause and a different arrival clause still make a mismatch, and speed or time does not."""

    @classmethod
    def setUpClass(cls):
        os.environ.pop(hazard_model.CLAUSE_ENV, None)
        cls.model = registry.load_model()

    def test_a_different_size_or_colour_that_arrived_is_a_mismatch(self):
        self.assertIn("not_as_described", flags(self.model, "Large ang inorder ko pero small ang dumating", "Dress for Women"))
        self.assertIn("not_as_described", flags(self.model, "Black ang inorder ko pero pink ang dumating", "Handheld Fan"))
        self.assertIn("not_as_described", flags(self.model, "Size 42 ang order ko, 43 ang pinadala", "Running Shoes"))

    def test_speed_and_time_are_not_a_mismatch(self):
        self.assertNotIn("not_as_described", flags(self.model, "Inorder ko kahapon pero dumating na ngayon", "Dress for Women"))
        self.assertNotIn("not_as_described", flags(self.model, "Inorder ko pero dumating agad, ang bilis", "Dress for Women"))

    def test_the_quoted_evidence_is_a_real_word_of_the_review(self):
        text = "Black ang inorder ko pero pink ang dumating"
        a = self.model.analyze_batch([text], [3], listing={"name": "Handheld Fan"})[0]
        span = a["review_evidence"]["not_as_described"]["spans"][0]
        self.assertEqual(text[span["review_start"]:span["review_end"]], span["text"])


class PackingDamageIsAboutThePacking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = registry.load_model()

    def test_damage_to_the_box_alone_is_not_a_defect(self):
        self.assertNotIn("defect", flags(self.model, "Yupi yupi ang box pero okay ang item", "Rice Cooker 1.8L"))

    def test_the_item_itself_damaged_in_the_same_review_still_is(self):
        self.assertIn("defect", flags(self.model, "The box was dented but the item is broken", "Rice Cooker 1.8L"))

    def test_a_conjunction_does_not_attach_a_damage_word_to_the_box(self):
        from defaketive_sentiment import product_category as pc
        self.assertFalse(pc._PACKING_DAMAGE.search("box at basag"))
        self.assertTrue(pc._PACKING_DAMAGE.search("yupi ang box"))


if __name__ == "__main__":
    unittest.main()
