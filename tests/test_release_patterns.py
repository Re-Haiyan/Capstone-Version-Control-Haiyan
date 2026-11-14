"""Release-audit changes: battery drain (policy B), spelling and spacing variants of "does not work", and their quoted evidence."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import registry  # noqa: E402

_model = None


def analyse(text, product, stars=2):
    global _model
    if _model is None:
        _model = registry.load_model()
    return _model.analyze_batch([text], [stars], listing={"name": product})[0]


def flags(text, product, stars=2):
    a = analyse(text, product, stars)
    return set(a["review_tags"]) | set(a.get("review_extra_tags") or [])


class BatteryDrain(unittest.TestCase):
    def test_a_bare_remark_is_not_a_defect(self):
        self.assertNotIn("defect", flags("Mabilis malowbat", "Handheld Fan"))
        self.assertNotIn("defect", flags("bilis malobat", "Handheld Fan"))

    def test_abrupt_or_measurable_failure_stays_a_defect(self):
        self.assertIn("defect", flags("Wala pang 10 min lobat na agad kahit full", "Power Bank 10000mAh"))
        self.assertIn("defect", flags("Kaka charge ko lang tapos lowbat kaagad", "Power Bank 10000mAh"))

    def test_a_charging_failure_is_a_defect(self):
        self.assertIn("defect", flags("Hindi na nagcha-charge, ayaw na mag-on", "Handheld Fan"))


class DoesNotWorkVariants(unittest.TestCase):
    CASES = [("ayw nman gumana", "Rice Cooker 1.8L"), ("Hindi rin nag charge", "Handheld Fan"), ("nag leak yung shampoo", "Shampoo 340ml"),
             ("hindi rin magamit ng ayos", "Rice Cooker 1.8L"), ("YOU CANNOT LOGIN TO ANY APPS", "Android Tablet"), ("napunit agad ang strap", "Backpack")]

    def test_each_variant_is_a_defect_with_quoted_evidence(self):
        for text, product in self.CASES:
            with self.subTest(text=text):
                a = analyse(text, product)
                self.assertIn("defect", a["review_tags"])
                entry = a["review_evidence"]["defect"]
                self.assertEqual(entry["state"], "keyword_span")
                for span in entry["spans"]:
                    self.assertEqual(text[span["review_start"]:span["review_end"]], span["text"])

    def test_not_having_used_it_yet_is_not_a_defect(self):
        self.assertNotIn("defect", flags("Hindi ko pa nagagamit, kakadating lang", "Rice Cooker 1.8L", 4))

    def test_a_problem_with_the_seller_is_not_a_product_defect(self):
        self.assertNotIn("defect", flags("may problema sa seller, matagal sumagot", "Rice Cooker 1.8L", 3))


if __name__ == "__main__":
    unittest.main()
