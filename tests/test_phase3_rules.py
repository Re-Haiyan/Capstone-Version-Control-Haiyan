"""Phase 3 extractor rules (asp3). Every sentence here is CONSTRUCTED for a unit test, never a real review and never evidence about accuracy.

The measured effect of these rules is in research/product_specific_conclusions/phase3/ (development and fresh final sets), not here.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import aspect_profiles  # noqa: E402
import aspects  # noqa: E402


def claims(text, stars=5, category=None, group=None):
    result = aspects.extract([{"comment_id": "c1", "content": text, "rating": stars}], category, group)
    return {(row["id"], polarity) for row, polarity, _ in aspects.iter_claims(result)}


class Asp3Rules(unittest.TestCase):
    def test_version(self):
        self.assertEqual(aspect_profiles.ASPECT_RULES_VERSION, "asp3")

    def test_labelled_prompt_answers_name_the_feature_and_the_direction(self):
        self.assertIn(("value", "positive"), claims("Price:good Quality:better"))
        self.assertIn(("build", "positive"), claims("Price:good Quality:better"))
        self.assertIn(("value", "negative"), claims("Price:poor"))
        self.assertIn(("build", "positive"), claims("Quality: 10"))
        self.assertIn(("build", "negative"), claims("Quality: 2"))

    def test_a_neutral_or_unlabelled_answer_is_not_a_statement(self):
        self.assertEqual(claims("Price:okay"), set())
        self.assertEqual(claims("good"), set())

    def test_a_list_of_suggested_phrases_is_not_an_answer(self):
        self.assertEqual(claims("Quality:Superior quality, Top-notch quality, Excellent finish,"), set())

    def test_a_lowercase_tag_list_is_not_a_customer_statement(self):
        text = "High safety, fast cooking, delicate small pot, strong durability, fast heating, reasonable design, suitable size, low noise, simple operation."
        self.assertEqual(claims(text, category="kitchenware"), set())

    def test_thanks_is_not_evidence_about_the_seller(self):
        self.assertNotIn(("seller", "positive"), claims("Thank you seller and Lazada\U0001F60D"))
        self.assertNotIn(("seller", "positive"), claims("salamat seller"))
        self.assertIn(("seller", "positive"), claims("Very responsive and accommodating seller"))

    def test_the_delivery_person_is_not_the_seller(self):
        self.assertNotIn(("seller", "positive"), claims("Responsive delivery man"))

    def test_matibay_is_durability_and_sturdy_is_build(self):
        got = claims("matibay siya")
        self.assertIn(("durability", "positive"), got)
        self.assertNotIn(("build", "positive"), got)
        self.assertIn(("build", "positive"), claims("sturdy and well made"))

    def test_wrong_colour_received_is_a_listing_mismatch_not_a_looks_complaint(self):
        got = claims("Different color received.", stars=2)
        self.assertIn(("matches_listing", "negative"), got)
        self.assertNotIn(("appearance", "negative"), got)

    def test_flimsy_packaging_is_not_a_build_complaint(self):
        got = claims("flimsy packaging, the box was crushed", stars=1)
        self.assertNotIn(("build", "negative"), got)
        self.assertIn(("packaging", "negative"), got)

    def test_a_question_about_authenticity_is_not_praise(self):
        self.assertNotIn(("authenticity", "positive"), claims("legit po ba to?"))

    def test_expanded_cues_read_ordinary_praise_and_complaints(self):
        self.assertIn(("value", "positive"), claims("nice price, super sulit"))
        self.assertIn(("functionality", "positive"), claims("It works quite well and serves its purpose"))
        self.assertIn(("ease", "positive"), claims("very easy to operate"))
        self.assertIn(("matches_listing", "negative"), claims("not as advertised", stars=2))
        self.assertIn(("delivery", "negative"), claims("took 19 days to arrive", stars=1))
        self.assertIn(("functionality", "negative"), claims("it doesn't work", stars=1))

    def test_a_praise_in_a_one_star_review_is_still_set_aside(self):
        self.assertEqual({c for c in claims("Comfort: good", stars=1) if c[1] == "positive" and c[0] in ("comfort", "functionality")}, set())

    def test_every_quotation_is_still_an_exact_substring_of_its_review(self):
        text = "Price:good Quality:better Taste:great. Thank you seller! Delivery was faster than expected."
        result = aspects.extract([{"comment_id": "c1", "content": text, "rating": 5}], None, None)
        for _row, _polarity, side in aspects.iter_claims(result):
            for quote in side["quotes"]:
                self.assertIn(quote["text"].rstrip("…").rstrip(), text)
                start, end = quote["span"]
                self.assertEqual(text[start:end], quote["text"].rstrip("…").rstrip() if not quote["text"].endswith("…") else text[start:end])


if __name__ == "__main__":
    unittest.main()
