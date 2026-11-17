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


PB, LED = "Power Bank 10000mAh", "Emergency LED Light"


def evidence(text, product, stars=2):
    return (analyse(text, product, stars).get("review_evidence") or {}).get("defect", {}).get("state")


class ChargingFailureBesideADrainRemark(unittest.TestCase):
    """A failure to charge said in the same breath as a drain remark is still a failure (policy B only sets the bare remark aside)."""

    def test_the_failure_is_found_as_a_quoted_keyword(self):
        for text in ("bilis ma lowbat ayaw pa ma charge", "madaling mag lowbat ang problema lang nya pag 30% na d na sya mag chacharge",
                     "bilis ma lowbat tas 100 lng nakalagay endi manlng nababawasan ayaw pa ma charge"):
            with self.subTest(text=text):
                self.assertIn("defect", flags(text, PB))
                self.assertEqual(evidence(text, PB), "keyword_span")

    def test_charging_wording_that_is_not_a_failure_is_not_matched(self):
        self.assertNotIn("defect", flags("mabilis mag charge, hindi mabagal", PB, 5))
        # The learned model (not these rules) still flags a few such sentences, before and after this change; the keyword rules must not.
        for text in ("hindi na ako mag-charge, tumatagal ng dalawang araw", "hindi na kailangan mag charge araw-araw, matagal ang battery"):
            with self.subTest(text=text):
                self.assertNotEqual(evidence(text, PB, 5), "keyword_span")


class AbruptDrain(unittest.TestCase):
    """Policy B: abrupt or measurable wording stays a defect even when its cue sits inside the phrase; a bare remark does not."""

    def test_abrupt_failures_are_defects(self):
        for text in ("isang minuto lang lowbat na agad", "wala pang 30kins lowbat na agad", "isang gamit lng lobat na", "30mins lang tapos lowbat na",
                     "kaka charge mo palang sa phone mo plowbat na agad", "charge ko cia magdamag tapos wala pang ilang menuto gusko wala na lowbat na agad"):
            with self.subTest(text=text):
                self.assertIn("defect", flags(text, PB, 1))

    def test_a_bare_remark_stays_a_remark_even_beside_praise_or_complaint_words(self):
        for text in ("Mabilis malowbat", "bilis malobat", "Maganda sana kaso ang bilis malowbat", "maganda ang tunog, sulit sa presyo, medyo mabilis malowbat lang",
                     "ok yung design at bass pero mabilis malowbat", "legit at original, mabilis malowbat nga lang"):
            with self.subTest(text=text):
                self.assertNotIn("defect", flags(text, PB, 3))

    def test_a_negated_drain_is_praise_whatever_cue_it_carries(self):
        for text in ("hindi agad malowbat, tumatagal ng 2 days", "hindi sya lowbat agad, ang tagal bago maubos", "10000mah talaga, hindi malowbat agad",
                     "hindi nalolowbat agad, tumatagal ng 8 oras", "kaka charge ko lang, ok naman, hindi lowbat agad", "di sya mabilis malowbat kahit full charge lang ng isang oras"):
            with self.subTest(text=text):
                self.assertNotIn("defect", flags(text, PB, 5))

    def test_wala_na_lowbat_means_the_battery_is_already_dead(self):
        self.assertIn("defect", flags("wala pang ilang menuto gusko wala na lowbat na agad", PB, 1))

    def test_a_measurable_wording_inside_praise_is_not_a_failure(self):
        for text in ("matagal malowbat kahit 10 mins lang i charge", "wala pang 5 minutes naka full charge na, ang bilis mag charge"):
            with self.subTest(text=text):
                self.assertNotIn("defect", flags(text, PB, 5))


class CombinedFailurePhrases(unittest.TestCase):
    """'not working' next to 'sira agad' used to be read as 'not (working) broken' and both phrases were cancelled."""

    def test_two_failure_phrases_together_are_still_a_defect(self):
        for text in ("Received but not working sira agad ung saksakan ng usb", "hindi gumagana sira agad ung saksakan ng usb", "not working sira agad"):
            with self.subTest(text=text):
                self.assertIn("defect", flags(text, LED))
                self.assertEqual(evidence(text, LED), "keyword_span")

    def test_each_phrase_alone_is_unchanged(self):
        self.assertIn("defect", flags("Received but not working", LED))
        self.assertIn("defect", flags("sira agad ung saksakan ng usb", LED))

    def test_real_denials_still_cancel(self):
        for text in ("walang sira, gumagana ng maayos", "no damage, working perfectly", "hindi sira ang box, gumagana naman",
                     "Not damaged at all, works great", "not broken, sound works fine"):
            with self.subTest(text=text):
                self.assertNotIn("defect", flags(text, LED, 5))


if __name__ == "__main__":
    unittest.main()
