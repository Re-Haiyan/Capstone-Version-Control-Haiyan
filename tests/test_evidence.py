"""Evidence states and offsets: every raised flag is either quoted from the review, tied to a listing comparison, or
explicitly marked as having no supporting words. Nothing is invented and nothing is suppressed unless the opt-in policy is on."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import evidence as ev  # noqa: E402
from defaketive_sentiment import registry  # noqa: E402


def sentence(index, raw, tags=(), extra=(), terms=(), extra_terms=(), learned=None, context=None):
    return {"index": index, "text_raw": raw, "tags": list(tags), "extra_tags": list(extra), "terms": list(terms),
            "extra_terms": list(extra_terms), "learned": learned or {}, "extra_context": context or {}}


class EvidenceUnit(unittest.TestCase):
    """Synthetic sentences, so these tests do not depend on any model score."""

    def test_a_keyword_flag_is_quoted_with_sentence_and_review_offsets(self):
        review = "Maganda ang item. Sira agad ang takip."
        sents = [sentence(0, "Maganda ang item."), sentence(1, "Sira agad ang takip.", tags=["defect"], terms=[{"category": "defect", "span": [0, 4]}])]
        out = ev.evidence_for_review(review, sents, ["defect"])
        span = out["defect"]["spans"][0]
        self.assertEqual(out["defect"]["state"], ev.KEYWORD_SPAN)
        self.assertEqual((span["start"], span["end"], span["text"]), (0, 4, "Sira"))
        self.assertEqual(review[span["review_start"]:span["review_end"]], "Sira")  # offsets point into the original text

    def test_a_flag_without_words_is_model_only_and_stays_raised(self):
        sents = [sentence(0, "Hindi ko gusto.", tags=["defect"], learned={"defect": 0.61})]
        out = ev.evidence_for_review("Hindi ko gusto.", sents, ["defect"])
        self.assertEqual(out["defect"]["state"], ev.MODEL_ONLY)
        self.assertEqual(out["defect"]["spans"], [])
        self.assertEqual(out["defect"]["model_score"], 0.61)
        self.assertIn("no supporting words", out["defect"]["note"])

    def test_a_listing_comparison_is_its_own_state(self):
        sents = [sentence(0, "Iba sa picture.", extra=["not_as_described"], context={"not_as_described": ["title"]})]
        out = ev.evidence_for_review("Iba sa picture.", sents, [], ["not_as_described"])
        self.assertEqual(out["not_as_described"]["state"], ev.LISTING_CONTEXT)
        self.assertEqual(out["not_as_described"]["listing_context"], {"0": ["title"]})

    def test_negated_excluded_or_out_of_range_terms_are_never_quoted(self):
        raw = "Hindi sira."
        terms = [{"category": "defect", "span": [6, 10], "negated": True}, {"category": "defect", "span": [6, 10], "excluded": "category"},
                 {"category": "defect", "span": [6, 99]}, {"category": "defect", "span": [3, 3]}]
        out = ev.evidence_for_review(raw, [sentence(0, raw, tags=["defect"], terms=terms)], ["defect"])
        self.assertEqual(out["defect"]["state"], ev.MODEL_ONLY)

    def test_a_sentence_that_cannot_be_located_has_no_review_offset_but_keeps_its_span(self):
        sents = [sentence(0, "changed text", tags=["defect"], terms=[{"category": "defect", "span": [0, 7]}])]
        out = ev.evidence_for_review("something else entirely", sents, ["defect"])
        self.assertIsNone(out["defect"]["spans"][0]["review_start"])
        self.assertEqual(out["defect"]["spans"][0]["text"], "changed")


class EvidencePolicy(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop(ev.POLICY_ENV, None)

    def tearDown(self):
        os.environ.pop(ev.POLICY_ENV, None)
        if self._saved is not None:
            os.environ[ev.POLICY_ENV] = self._saved

    def _case(self):
        sents = [sentence(0, "Hindi ko gusto.", tags=["defect", "safety"], learned={"defect": 0.6, "safety": 0.5})]
        evidence = ev.evidence_for_review("Hindi ko gusto.", sents, ["defect", "safety"])
        return sents, evidence

    def test_default_keeps_every_flag(self):
        sents, evidence = self._case()
        tags, extra, dropped = ev.apply_policy(sents, ["defect", "safety"], [], evidence)
        self.assertEqual((tags, dropped), (["defect", "safety"], []))

    def test_require_drops_model_only_defect_but_never_safety_and_says_so(self):
        os.environ[ev.POLICY_ENV] = ev.POLICY_REQUIRE
        sents, evidence = self._case()
        tags, extra, dropped = ev.apply_policy(sents, ["defect", "safety"], [], evidence)
        self.assertEqual(tags, ["safety"])
        self.assertEqual([d["flag"] for d in dropped], ["defect"])
        self.assertEqual(dropped[0]["reason"], "model_only_no_supporting_words")
        self.assertEqual(sents[0]["tags"], ["safety"])


class EvidenceEndToEnd(unittest.TestCase):
    """The real pipeline on English, Filipino and Taglish reviews."""

    @classmethod
    def setUpClass(cls):
        os.environ.pop(ev.POLICY_ENV, None)
        cls.model = registry.load_model()

    def run_review(self, text, product, stars=2):
        return self.model.analyze_batch([text], [stars], listing={"name": product})[0]

    def assertQuotes(self, text, evidence_entry):
        for span in evidence_entry["spans"]:
            self.assertEqual(text[span["review_start"]:span["review_end"]], span["text"], "offsets must point into the original review")

    def test_english(self):
        text = "The charger started smoking after an hour. Delivery was fast."
        a = self.run_review(text, "Phone Charger 20W")
        self.assertEqual(a["review_evidence"]["safety"]["state"], ev.KEYWORD_SPAN)
        self.assertQuotes(text, a["review_evidence"]["safety"])
        self.assertEqual(a["review_evidence"]["safety"]["spans"][0]["sentence"], 0)

    def test_filipino(self):
        text = "Dumating na basag at sira ang takip."
        a = self.run_review(text, "Rice Cooker 1.8L")
        self.assertIn("defect", a["review_evidence"])
        self.assertQuotes(text, a["review_evidence"]["defect"])

    def test_taglish_with_the_flag_in_the_second_clause(self):
        text = "Maganda ang design pero madaling masira."
        a = self.run_review(text, "Backpack", stars=3)
        self.assertTrue(set(a["review_evidence"]) & {"defect", "quality"})
        for entry in a["review_evidence"].values():
            self.assertQuotes(text, entry)

    def test_negation_raises_nothing_to_quote(self):
        a = self.run_review("hindi sira at gumagana ng maayos", "Mini Fan", stars=5)
        self.assertNotIn("defect", a["review_evidence"])

    def test_multiple_flags_each_have_their_own_spans(self):
        text = "Peke ito at sira agad, hindi gumana."
        a = self.run_review(text, "Power Bank 10000mAh", stars=1)
        self.assertEqual(a["review_evidence"]["counterfeit"]["state"], ev.KEYWORD_SPAN)
        self.assertEqual(a["review_evidence"]["defect"]["state"], ev.KEYWORD_SPAN)
        for entry in a["review_evidence"].values():
            self.assertQuotes(text, entry)

    def test_a_sentence_boundary_keeps_offsets_in_the_whole_review(self):
        text = "Ok naman ang delivery. Umusok ang charger kagabi."
        a = self.run_review(text, "Phone Charger 20W")
        span = a["review_evidence"]["safety"]["spans"][0]
        self.assertGreater(span["review_start"], span["start"])  # the second sentence starts later in the review
        self.assertQuotes(text, a["review_evidence"]["safety"])

    def test_the_fields_are_additive(self):
        a = self.run_review("Umusok ang charger.", "Phone Charger 20W")
        for key in ("review_tags", "sentences", "review_high_confidence", "sentiment", "label"):
            self.assertIn(key, a)
        self.assertNotIn("review_evidence_dropped", a)  # nothing is dropped unless the policy is on


class EvidencePolicyShadow(unittest.TestCase):
    """DEFAKETIVE_EVIDENCE_POLICY=shadow reports what 'require' would do and changes nothing."""

    MODEL_ONLY_REVIEW = "nakakatakot icharge ung iphone ko dto"  # a learned-layer defect flag with no supporting words (deterministic)

    @classmethod
    def setUpClass(cls):
        cls.model = registry.load_model()

    def setUp(self):
        os.environ.pop(ev.POLICY_ENV, None)

    tearDown = setUp

    def run_review(self, text=None, product="Phone Cable"):
        return self.model.analyze_batch([text or self.MODEL_ONLY_REVIEW], [2], listing={"name": product})[0]

    def test_shadow_changes_no_flag_and_lists_what_would_be_dropped(self):
        base = self.run_review()
        self.assertIn("defect", base["review_tags"])
        self.assertEqual(base["review_evidence"]["defect"]["state"], ev.MODEL_ONLY)
        os.environ[ev.POLICY_ENV] = ev.POLICY_SHADOW
        shadow = self.run_review()
        self.assertEqual(shadow["review_tags"], base["review_tags"])
        self.assertNotIn("review_evidence_dropped", shadow)
        self.assertEqual([d["flag"] for d in shadow["review_evidence_would_drop"]], ["defect"])

    def test_nothing_is_reported_when_the_policy_is_not_shadow(self):
        self.assertNotIn("review_evidence_would_drop", self.run_review())

    def test_safety_is_never_in_the_shadow_list(self):
        os.environ[ev.POLICY_ENV] = ev.POLICY_SHADOW
        a = self.run_review("Umusok ang charger at amoy sunog, muntik nang masunog", "Phone Charger 20W")
        self.assertIn("safety", a["review_tags"])
        self.assertNotIn("safety", [d["flag"] for d in a.get("review_evidence_would_drop") or []])

    def test_the_shadow_verdict_equals_what_require_then_produces(self):
        from defaketive_sentiment.product_badges import ProductBadgeAggregator

        texts = [self.MODEL_ONLY_REVIEW] * 14 + ["Maganda ang product, sulit na sulit", "Okay naman, ayos ang quality, recommended seller"] * 12
        stars = [2] * 14 + [5] * 24

        def summarise():
            analyses = self.model.analyze_batch(texts, stars, listing={"name": "Phone Cable"})
            return ProductBadgeAggregator().summarize(analyses, reviews_available=len(texts), product_type="charger_cable")

        real = summarise()
        self.assertNotIn("shadow_evidence_policy", real)
        os.environ[ev.POLICY_ENV] = ev.POLICY_SHADOW
        shadowed = summarise()
        self.assertEqual(shadowed["flags"]["defect"]["flagged_reviews"], real["flags"]["defect"]["flagged_reviews"])  # the real counts are untouched
        self.assertEqual(shadowed["verdict"]["state"], real["verdict"]["state"])
        block = shadowed["shadow_evidence_policy"]
        self.assertEqual(block["dropped_flags"].get("defect"), 14)
        os.environ[ev.POLICY_ENV] = ev.POLICY_REQUIRE
        required = summarise()
        self.assertEqual(block["verdict_state"], required["verdict"]["state"])
        self.assertEqual(block["flagged_reviews"]["defect"], required["flags"]["defect"]["flagged_reviews"])


if __name__ == "__main__":
    unittest.main()
