"""Panel flow: XLM-R first, title-derived category check, independent hazards.

The contextual stage is informational ONLY. Historical silver labels did not
qualify any automatic replacement of authoritative model predictions.
"""
from __future__ import annotations

from pathlib import Path
import copy
import os
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT / "backend"),str(ROOT / "backend/sentiment-analysis")]
from defaketive_sentiment import category_context as context  # noqa: E402
from defaketive_sentiment.product_category import CATEGORIES, OTHER  # noqa: E402
sys.path.insert(0,str(ROOT / "tests"))
from test_product_category import TITLES, PC3_TITLES  # noqa: E402
from defaketive_sentiment.hazard_model import HazardBadgeModel, LexiconHazardTagger  # noqa: E402


class StageContext(unittest.TestCase):
    def evaluate(self, name, review, label="neutral"):
        return context.check(review, {"name":name}, label)

    def test_full_product_taxonomy_exactly_49_plus_other(self):
        self.assertEqual(len(CATEGORIES),50)
        profiles = context._profiles()["profiles"]
        self.assertEqual(len(profiles),49)
        self.assertEqual(set(profiles),set(CATEGORIES)-{OTHER})
        for category, profile in profiles.items():
            with self.subTest(category=category):
                self.assertTrue(profile["positive_phrases"])
                self.assertTrue(profile["negative_phrases"])
                self.assertTrue(profile["expected_behavior_phrases"])

    def test_each_category_has_a_reachable_title_and_phrase(self):
        # Titles are already validated by the shipped marketplace taxonomy tests.
        examples = {}
        for title, category in [*TITLES.items(), *PC3_TITLES.items()]:
            if category != OTHER:
                examples.setdefault(category,title)
        self.assertEqual(set(examples),set(context._profiles()["profiles"]))
        for category,title in examples.items():
            with self.subTest(category=category):
                profile=context._profiles()["profiles"][category]
                pos=self.evaluate(title,profile["positive_phrases"][0],"neutral")
                neg=self.evaluate(title,profile["negative_phrases"][0],"neutral")
                self.assertEqual(pos["product_category"],category)
                self.assertEqual(pos["context_signal"],"positive",pos)
                self.assertEqual(neg["context_signal"],"negative",neg)
                self.assertFalse(pos["sentiment_overridden"])
                self.assertFalse(neg["sentiment_overridden"])

    def test_ambiguous_term_meanings_follow_product(self):
        cases=(
            ("Samsung Galaxy A15 Smartphone", "Ang nipis, ang ganda!", "positive"),
            ("Cotton T-Shirt Oversized", "Sobrang nipis ng tela.", "negative"),
            ("20000mAh Power Bank", "Sobrang init habang nagcha-charge.", "negative"),
            ("Instant Coffee 3 in 1", "Mainit at bagong luto.", "positive"),
        )
        for title,review,expected in cases:
            with self.subTest(title=title):
                result=self.evaluate(title,review)
                self.assertEqual(result["context_signal"],expected,result)
                self.assertEqual(result["status"],"differs")
                self.assertEqual(result["initial_label"],"neutral")
                self.assertFalse(result["sentiment_overridden"])
                self.assertFalse(result["used_for_decision"])
        same=self.evaluate("Cotton T-shirt","Sobrang nipis ng tela.","negative")
        self.assertEqual(same["status"],"agrees")

    def test_explicit_denial_and_conflicting_reviews_fail_closed(self):
        cases=(
            ("Instant Coffee", "Hindi mainit at bagong luto."),
            ("20000mAh Power Bank", "Hindi sobrang init habang nagcha-charge."),
            ("Headphones Audio", "Clear sound but sound keeps crackling."),
            ("Smart TV Display", "No dead pixels on screen."),
        )
        for title,review in cases:
            with self.subTest(title=title,review=review):
                result=self.evaluate(title,review,"positive")
                self.assertEqual(result["status"],"ambiguous",result)
                self.assertIsNone(result["context_signal"])

    def test_no_signal_and_unrecognized_category_do_not_force_a_guess(self):
        self.assertEqual(self.evaluate("Unknown Marketplace Listing XYZ","Sobrang init")["status"],"unclassified")
        self.assertEqual(self.evaluate("Instant Coffee","Masarap naman")["status"],"no_signal")
        self.assertIsNone(self.evaluate("Instant Coffee","Sarap", "unknown"))
        self.assertIsNone(context.check("Sarap",None,"negative"))
        self.assertEqual(self.evaluate("Instant Coffee","x"*5001)["status"],"no_signal")
        self.assertEqual(self.evaluate("Instant Coffee",123)["status"],"no_signal")
        self.assertIsNone(self.evaluate("Instant Coffee","Masarap",None))

    def test_missing_profiles_fail_closed_without_changing_model_decisions(self):
        with mock.patch.object(context, "_profiles", side_effect=OSError("context file missing")):
            report=self.evaluate("Instant Coffee", "Mainit at bagong luto", "negative")
        self.assertEqual(report["status"],"unavailable")
        self.assertFalse(report["sentiment_overridden"])

    def test_contraction_negation_abstains(self):
        review="Don't say mainit at bagong luto"
        self.assertEqual(self.evaluate("Instant Coffee",review,"negative")["status"],"ambiguous")

    def test_profile_matching_requires_whole_words(self):
        # The explicit "mainit at bagong luto" praise is NOT present as a
        # complete phrase. A generic "mainit" may still be expected behavior.
        similar = self.evaluate("Instant Coffee","Mainit at bagong lutong-luto")
        self.assertIsNone(similar["context_signal"])
        self.assertNotEqual(similar["matched_profile_phrase"], "mainit at bagong luto")
        self.assertEqual(self.evaluate("Instant Coffee","Mainit at bagong luto!")["context_signal"],"positive")


class FakeXLMR:
    model_version="synthetic-review-label-v1"
    def fingerprint(self,text):
        return str(text).lower()
    def analyze(self,text,rating=None):
        return {
            "label":"neutral", "model_version":self.model_version,
            "classifier":{"probabilities":{"negative":.2,"neutral":.6,"positive":.2}},
            "risk":{"detected":False,"categories":[],"evidence":[]},
            "sentiment_evidence":[],"scores":{},
        }


class EndToEndPanelStage(unittest.TestCase):
    def test_stage_order_and_hazard_independence(self):
        fake=FakeXLMR()
        hazard=HazardBadgeModel(
            allow_unqualified=True,
            tagger=LexiconHazardTagger(rules="0.4",counterfeit_rules="c2"),
            sentiment_model=fake,
        )
        text="Sobrang nipis ng tela, see through."
        with mock.patch.dict(os.environ,{"DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW":""}):
            result=hazard.analyze(text,1,listing={"name":"Cotton T-shirt"})
        # Always on: the stage records category context, but this cannot
        # modify the authoritative label, warning flags or verdict.
        ctx=result["sentiment"]["category_context"]
        self.assertEqual(result["label"],"neutral")
        self.assertEqual(ctx["initial_label"],"neutral")
        self.assertEqual(ctx["context_signal"],"negative")
        self.assertEqual(ctx["status"],"differs")
        self.assertFalse(ctx["sentiment_overridden"])
        self.assertFalse(ctx["used_for_decision"])
        self.assertNotIn("category_shadow",result["sentiment"])
        with mock.patch.dict(os.environ,{"DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW":"shadow"}):
            audit=hazard.analyze(text,1,listing={"name":"Cotton T-shirt"})
        self.assertEqual(audit["label"],result["label"])
        self.assertEqual(audit["review_tags"],result["review_tags"])
        self.assertEqual(audit.get("review_extra_tags"),result.get("review_extra_tags"))
        self.assertEqual(audit["sentiment"]["category_context"],ctx)
        self.assertEqual(audit["sentiment"]["category_shadow"]["used_for_decision"],False)

    def test_no_title_returns_old_schema_without_context(self):
        hazard=HazardBadgeModel(allow_unqualified=True,tagger=LexiconHazardTagger(rules="0.4",counterfeit_rules="c2"),sentiment_model=FakeXLMR())
        result=hazard.analyze("My product is fine",5)
        self.assertNotIn("category_context",result["sentiment"])


if __name__=="__main__":
    unittest.main()
