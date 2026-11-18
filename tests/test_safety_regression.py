"""Safety regression guard (release blocker check): benign wording must not raise a safety flag, and genuine hazards that use the same words must.

The cases are generic phrasings of each rule, not rows of the historical test file. They compare nothing with labels.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import registry  # noqa: E402

_model = None


def safety(text, product, stars=3):
    global _model
    if _model is None:
        _model = registry.load_model()
    a = _model.analyze_batch([text], [stars], listing={"name": product})[0]
    return "safety" in set(a["review_tags"])


BOTTLE = "Anti-colic Baby Bottle 4-pack"
BAND = "Smart Band 1.47 inch"
SOAP = "Antiseptic Skin Cleanser 120ml"
CHEESE = "Cheese 900G"


class FeatureClaimsAreNotHazards(unittest.TestCase):
    def test_listing_boilerplate(self):
        self.assertFalse(safety("Ribbed texture prevents collapse, Wide neck for easy cleaning", BOTTLE, 5))
        self.assertFalse(safety("Tracks the steps and calories burned", BAND, 5))
        self.assertFalse(safety("Relieves itching instantly, gentle on the skin", SOAP, 5))
        self.assertFalse(safety("di ko pa nababatad para sa burn test, so far gumagana naman", "LED Monitor", 5))


class NormalHeatingIsNotAReportedSafetyIssue(unittest.TestCase):
    """Real-world screenshot reproductions and non-heating counterexamples.

    Tagger-only checks isolate the rule independently of the model's learned
    filter, while the shipped model still undergoes a separate paired VM audit.
    """

    def _tag(self, sentence, title):
        from defaketive_sentiment.hazard_model import LexiconHazardTagger, SHIPPED_COUNTERFEIT_RULES
        # Production runs c2, which enables listing-derived product category.
        # A legacy c1 research tagger intentionally has no listing context.
        tagger = LexiconHazardTagger(
            rules="0.4", counterfeit_rules=SHIPPED_COUNTERFEIT_RULES, learned=None
        )
        return tagger.tag_review(sentence, 5, listing={"name": title})

    def test_screenshot_water_heater_praise_is_not_safety(self):
        texts = (
            "Not only does it look beautiful, but it also heats up very quickly, and you can feel the warmth in just a few seconds.",
            "It is small and beautiful, has good water output, and heats up quickly. I give it a thumbs up.",
            "Water heater heats up quickly and works great.",
            "The rice cooker heats up fast and cooks evenly.",
            "The air fryer heats up very quickly and works well.",
            "Hair straightener heats up rapidly and is easy to use.",
        )
        names = (
            "Instant Water Heater 3500W",
            "Instant Water Heater 3500W",
            "Electric Water Heater",
            "Rice Cooker 1.8L",
            "Air Fryer 4L",
            "Ceramic Hair Straightener",
        )
        for title, review in zip(names, texts):
            with self.subTest(title=title, review=review):
                analyses = self._tag(review, title)
                self.assertFalse(any("safety" in item["tags"] for item in analyses), analyses)

    def test_unrelated_electronics_still_flag_rapid_heating(self):
        for title in ("Power Bank 20000mAh", "Smartphone 128GB", "USB Fast Charger 30W"):
            with self.subTest(title=title):
                self.assertTrue(any(
                    "safety" in s["tags"]
                    for s in self._tag("It heats up very quickly while charging", title)
                ))

    def test_heating_product_with_actual_warning_is_never_exempt(self):
        samples = (
            "The water heater heats up quickly, but the plug starts smoking.",
            "It heats up quickly and burned my hand on the handle.",
            "The heater heats up too hot and smells like burning plastic.",
            "It heats up quickly, but the power cord gets hot.",
            "It heats up quickly and sparks come out from the socket.",
        )
        for text in samples:
            with self.subTest(text=text):
                self.assertTrue(any(
                    "safety" in s["tags"]
                    for s in self._tag(text, "Instant Water Heater 3500W")
                ))


class RealHazardsWithTheSameWordsStay(unittest.TestCase):
    def test_collapse(self):
        self.assertTrue(safety("The crib collapsed while my baby was in it", BOTTLE, 1))
        self.assertTrue(safety("Bumagsak ang crib habang nasa loob ang baby ko", BOTTLE, 1))

    def test_burn(self):
        self.assertTrue(safety("The strap gave me a burn on my wrist after exercise", BAND, 1))
        self.assertTrue(safety("It tracks calories burned but the charger smelled burning and smoked", BAND, 1))

    def test_a_wish_to_prevent_a_burnt_smell_is_not_a_feature_claim(self):
        self.assertTrue(safety("Anyone know what to do to prevent that burnt plastic smell? it is on my food", "Air Fryer", 3))
        self.assertFalse(safety("Leak-proof and burn-resistant design, prevents leaks", "Travel Mug", 5))

    def test_itching_and_rash(self):
        self.assertTrue(safety("Relieves itching pero nagka rash ako after using it", SOAP, 2))
        self.assertTrue(safety("Nangati ako at nagka rash after using this soap", SOAP, 1))


class ExpiredItems(unittest.TestCase):
    """A date can clear a review ("expiry date 2027 pa"), never a sentence that says the item itself is expired."""

    def test_a_far_date_or_a_short_shelf_life_is_not_an_expired_item(self):
        self.assertFalse(safety("expired date september 2027 so fine", CHEESE, 5))
        self.assertFalse(safety("maayos din yung packaging safe na safe 2028 pa yung expired kaya fresh talaga", CHEESE, 5))
        self.assertFalse(safety("no good, the expired date September 2026 is too early so I dont order again", CHEESE, 3))

    def test_an_expired_item_stays_a_hazard_even_when_a_date_is_quoted(self):
        for text in (
            "Expired yung natanggap ko, expiry date March 2024 pa",
            "the expiry date was 2023, it was already expired",
            "Expired na yung dumating, September 2025 pa ang expiry date",
            "the product was already expired when it arrived",
            "nagexpire na agad, paso na ang expiry date pagdating",
            "The item is expired. Do not buy",
        ):
            with self.subTest(text=text):
                self.assertTrue(safety(text, CHEESE, 1))


if __name__ == "__main__":
    unittest.main()
