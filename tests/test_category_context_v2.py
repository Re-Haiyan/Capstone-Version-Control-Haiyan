"""Cross-category contextual interpretation regressions.

These assert safe behavior for 49 categories and selected product subtypes,
without claiming empirical improvement in sentiment F1. The *real* XLM-R
and independent five-label hazard model remain authoritative.
"""
from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"backend"),str(ROOT/"backend/sentiment-analysis"),str(ROOT/"tests")]

from defaketive_sentiment import category_context as cc  # noqa: E402
from defaketive_sentiment.product_category import CATEGORIES  # noqa: E402
from defaketive_sentiment.hazard_model import HazardBadgeModel, LexiconHazardTagger  # noqa: E402
from test_product_category import TITLES, PC3_TITLES  # noqa: E402


class TestCategoryContextV2(unittest.TestCase):
    def classify(self,title,review,label="neutral"):
        return cc.check(review,{"name":title},label)

    def test_all_49_types_have_reachable_explicit_and_expected_profiles(self):
        examples={}
        for title,category in [*TITLES.items(),*PC3_TITLES.items()]:
            if category!="other":
                examples.setdefault(category,title)
        self.assertEqual(set(examples),set(CATEGORIES)-{"other"})
        self.assertEqual(cc.REVISION,"category-context-v2")
        for category,title in examples.items():
            with self.subTest(category=category):
                profile=cc._profiles()["profiles"][category]
                result_pos=self.classify(title,profile["positive_phrases"][0])
                result_neg=self.classify(title,profile["negative_phrases"][0])
                result_expected=self.classify(title,profile["expected_behavior_phrases"][0])
                self.assertEqual(result_pos["context_signal"],"positive",result_pos)
                self.assertEqual(result_neg["context_signal"],"negative",result_neg)
                self.assertEqual(result_expected["status"],"expected_behavior",result_expected)
                for output in (result_pos,result_neg,result_expected):
                    self.assertEqual(output["initial_label"],"neutral")
                    self.assertFalse(output["used_for_decision"])
                    self.assertFalse(output["sentiment_overridden"])
                self.assertIsNone(result_expected["context_signal"])

    def test_expected_operation_is_not_a_sentiment_override(self):
        examples=(
            ("Portable Electric Heater 1500W","Mainit ang heater","heater"),
            ("Window Air Conditioner 1HP","Malamig ang hangin","air_conditioner"),
            ("Electric Stand Fan 16 inch","Malakas ang hangin","fan"),
            ("Digital Refrigerator Two Door","Malamig sa loob","refrigerator"),
            ("Bluetooth Speaker Loud","Malakas ang tunog","speaker"),
            ("Motorcycle Muffler Exhaust","Maingay ang pipe","exhaust"),
            ("Dumbbell Adjustable 10kg","Mabigat ang dumbbell","weights"),
            ("Instant Coffee 3 in 1","Mainit","hot_prepared"),
            ("Vanilla Ice Cream Frozen Dessert","Cold ice cream","cold_frozen"),
            ("Nonstick Frying Pan","Mainit ang pan","cookware"),
        )
        for title,review,subtype in examples:
            with self.subTest(title=title):
                result=self.classify(title,review,"negative")
                self.assertEqual(result["subproduct"],subtype,result)
                self.assertEqual(result["status"],"expected_behavior",result)
                self.assertIsNone(result["context_signal"])
                self.assertEqual(result["initial_label"],"negative")
                self.assertFalse(result["sentiment_overridden"])

    def test_no_cross_product_rule_leakage(self):
        self.assertNotEqual(self.classify("Portable Electric Heater","Mainit")["status"],"differs")
        # An aircon being hot is NOT the expected function of a heater.
        self.assertNotEqual(self.classify("Air Conditioner 1HP","Mainit")["status"],"expected_behavior")
        self.assertNotEqual(self.classify("Ice Cream Frozen Dessert","Mainit")["status"],"expected_behavior")
        self.assertNotEqual(self.classify("Smartphone 128GB","Mainit")["status"],"expected_behavior")
        self.assertNotEqual(self.classify("Motorcycle Helmet","Maingay ang pipe")["status"],"expected_behavior")

    def test_actual_failures_remain_negative_context_candidates(self):
        samples=(
            ("Portable Electric Heater","Heater not heating"),
            ("Portable Electric Heater","Hindi umiinit ang heater"),
            ("Air Conditioner 1HP","Hindi lumalamig ang aircon"),
            ("Speaker Bluetooth","Basag ang tunog"),
            ("Cotton T Shirt","Sobrang nipis ng tela"),
            ("Mobile Phone Smartphone","Touchscreen unresponsive"),
            ("Electric Drill Tool Set","Drill bit snapped"),
            ("Running Shoes Footwear","Sole came off"),
            ("Ice Cream Frozen Dessert","Ice cream arrived melted"),
            ("Nonstick Frying Pan","Pan handle burns"),
        )
        for title,review in samples:
            with self.subTest(title=title,review=review):
                result=self.classify(title,review)
                self.assertEqual(result["context_signal"],"negative",result)
                self.assertFalse(result["sentiment_overridden"])

    def test_hazards_and_excess_cannot_be_marked_expected(self):
        reviews=(
            "Sobrang mainit ang heater",
            "Mainit ang plug ng heater",
            "Mainit ang heater pero umusok",
            "Too hot to touch ang handle",
            "Mainit ang heater at may sparks",
        )
        for review in reviews:
            with self.subTest(review=review):
                result=self.classify("Portable Electric Heater 1500W",review)
                self.assertNotEqual(result["status"],"expected_behavior",result)
                self.assertNotEqual(result["context_signal"],"positive",result)

    def test_expected_feature_with_other_complaint_must_abstain(self):
        samples=(
            ("Portable Heater","Mainit ang heater pero sira ang timer"),
            ("Portable Heater","Mainit ang heater but broken switch"),
            ("Bluetooth Speaker","Malakas ang tunog pero basag ang mic"),
            ("Adjustable Dumbbell","Mabigat ang dumbbell but cracked handle"),
            ("Nonstick Frying Pan","Mainit ang pan ngunit damaged ang handle"),
            ("Acoustic Guitar","Malakas ang tunog but awful quality"),
            ("Instant Coffee","Mainit ang pagkain pero panis"),
        )
        for title,review in samples:
            with self.subTest(title=title,review=review):
                result=self.classify(title,review)
                self.assertEqual(result["status"],"ambiguous",result)
                self.assertIsNone(result["context_signal"])

    def test_explicit_functional_failure_in_expected_product_is_negative(self):
        samples=(
            ("Portable Electric Heater","Hindi mainit ang heater"),
            ("Portable Electric Heater","Di umiinit ang heater"),
            ("Window Air Conditioner","Hindi malamig ang aircon"),
            ("Window Air Conditioner","Mainit ang buga ng aircon"),
            ("Bluetooth Speaker","Basag ang speaker"),
        )
        for title,review in samples:
            with self.subTest(title=title,review=review):
                result=self.classify(title,review)
                self.assertEqual(result["context_signal"],"negative",result)
                self.assertFalse(result["sentiment_overridden"])

    def test_negation_comparisons_and_mixed_opinions_abstain(self):
        samples=(
            ("Portable Electric Heater","Hindi ganun kainit ang heater"),
            ("Bluetooth Speaker","Hindi malinaw ang tunog"),
            ("Earbuds Audio","Clear sound but sound keeps crackling"),
            ("Power Bank","Hindi sobrang init habang nagcha-charge"),
            ("Instant Coffee","Hindi mainit at bagong luto"),
            ("Frying Pan","Hindi mainit ang pan"),
            ("Running Shoes","Not comfortable shoes"),
        )
        for title,review in samples:
            with self.subTest(title=title,review=review):
                result=self.classify(title,review)
                self.assertEqual(result["status"],"ambiguous",result)
                self.assertIsNone(result["context_signal"])

    def test_ambiguous_traits_are_not_automatically_positive_or_negative(self):
        samples=(
            ("Bluetooth Speaker","Loud"),
            ("Smartphone","Thin"),
            ("Cotton T Shirt","Thin"),
            ("Running Shoes","Tight"),
            ("Acoustic Guitar","Bright"),
            ("Frying Pan","Thin"),
            ("Yoga Mat","Heavy"),
        )
        for title,review in samples:
            with self.subTest(title=title,review=review):
                result=self.classify(title,review)
                self.assertIsNone(result["context_signal"],result)

    def test_other_and_invalid_input_abstain(self):
        self.assertEqual(self.classify("Random unknown listing ABC","Sobrang init")["status"],"unclassified")
        self.assertIsNone(cc.check("hot",None,"positive"))
        self.assertIsNone(cc.check("hot",{"name":"Heater"},"unknown"))
        with mock.patch.object(cc,"_profiles",side_effect=OSError("missing file")):
            result=self.classify("Portable Heater","Mainit")
            self.assertEqual(result["status"],"unavailable")


class SyntheticSentiment:
    model_version="synthetic-context-v2"
    def fingerprint(self,text): return str(text).casefold()
    def analyze(self,text,rating=None):
        return {"label":"neutral","classifier":{"probabilities":{}},"model_version":self.model_version,"risk":{},"scores":{}}


class TestHazardIndependence(unittest.TestCase):
    def test_category_context_can_never_change_any_authoritative_model_output(self):
        model=HazardBadgeModel(
            allow_unqualified=True,
            tagger=LexiconHazardTagger(rules="0.4",counterfeit_rules="c2"),
            sentiment_model=SyntheticSentiment(),
        )
        inputs=(
            ("Portable Heater","Mainit ang heater",5),
            ("Portable Heater","Mainit ang heater pero nag sparks ang plug",1),
            ("Portable Heater","Hindi umiinit ang heater",1),
            ("Powerbank 20000mAh","Sobrang init habang nagcha-charge",1),
            ("Cotton T Shirt","Sobrang nipis ng tela",1),
            ("Speaker Bluetooth","Malakas ang volume",5),
            ("Ice Cream Frozen Dessert","Ice cream arrived melted",1),
            ("Nonstick Frying Pan","Mainit ang pan",5),
            ("Dumbbell Adjustable","Mabigat ang dumbbell",5),
            ("Electric Drill Tool Set","Drill bit snapped",1),
        )
        with mock.patch.dict(os.environ,{"DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW":""}):
            for title,review,rating in inputs:
                with self.subTest(title=title,review=review):
                    listing={"name":title}
                    with mock.patch.object(cc,"check",return_value=None):
                        baseline=model.analyze(review,rating,listing=listing)
                    candidate=model.analyze(review,rating,listing=listing)
                    self.assertIn("category_context",candidate["sentiment"])
                    self.assertFalse(candidate["sentiment"]["category_context"]["used_for_decision"])
                    self.assertFalse(candidate["sentiment"]["category_context"]["sentiment_overridden"])
                    preserved=copy.deepcopy(candidate)
                    del preserved["sentiment"]["category_context"]
                    self.assertEqual(preserved,baseline)


if __name__=="__main__":
    unittest.main()
