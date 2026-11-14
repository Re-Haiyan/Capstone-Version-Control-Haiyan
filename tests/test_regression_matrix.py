"""Regression matrix for the review checker (research round): each case is a review, a product, and the flags it must
(or must not) raise. Cases come from the scenarios listed in the research brief, in English, Filipino and Taglish.
Spans are checked against the original text: every highlighted range must lie inside its sentence and quote real characters.
"""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import registry  # noqa: E402

_model = None


def analyze(text, product, stars=3):
    global _model
    if _model is None:
        _model = registry.load_model()
    return _model.analyze_batch([text], [stars], listing={"name": product})[0]


def flags(text, product, stars=3):
    a = analyze(text, product, stars)
    return set(a.get("review_tags") or []) | set(a.get("review_extra_tags") or [])


# (text, product, must_have, must_not_have)
CASES = [
    # negation
    ("hindi sira, gumagana ng maayos", "Mini Fan", set(), {"defect"}),
    ("not defective at all, works great", "Blender", set(), {"defect"}),
    ("walang amoy sunog, okay naman", "Phone Charger 20W", set(), {"safety"}),
    ("no rash, no itching, gentle on my skin", "Facial Cleanser", set(), {"safety"}),
    # counterfeit
    ("peke ito, hindi original, scam ang seller", "Wireless Earbuds", {"counterfeit"}, set()),
    ("akala ko peke pero original pala, sulit", "Wireless Earbuds", set(), {"counterfeit"}),
    # quality and praise with negative-looking words
    ("sobrang nipis ng tela, parang papel, mukhang cheap", "Dress for Women", {"quality"}, set()),
    ("hindi mukhang mumurahin, sulit ang presyo", "Backpack", set(), {"quality"}),
    ("killer deal, ang sakit sa mata ng ganda ng kulay", "Dress for Women", set(), {"defect", "quality"}),
    # real defects and missing accessories
    ("hindi gumana mula pagdating, sira agad", "Rice Cooker 1.8L", {"defect"}, set()),
    ("walang charger na kasama, kulang ang laman ng box", "Handheld Fan", {"not_as_described"}, set()),
    # box damage versus product damage
    ("yupi yupi ang box pero okay ang item, maayos ang laman", "Rice Cooker 1.8L", set(), {"defect"}),
    ("dumating na basag ang item at sira ang takip", "Rice Cooker 1.8L", {"defect"}, set()),
    # delivery-only
    ("sobrang tagal dumating at hindi nagrereply ang seller, pero okay ang product", "Bluetooth Speaker", set(), {"defect", "counterfeit"}),
    # warmth versus dangerous overheating
    ("medyo mainit lang ang charger kapag matagal gamitin, normal naman", "Phone Charger 20W", set(), {"safety"}),
    ("umusok ang charger at amoy sunog, muntik nang masunog", "Phone Charger 20W", {"safety"}, set()),
    ("init na init ang panahon ngayon pero maganda ang tela", "T-shirt", set(), {"safety"}),
    # skin, food
    ("nagka-rashes at makati ang mukha ko pagkatapos gamitin", "Facial Cleanser", {"safety"}, set()),
    ("expired na pala ang dumating, panis ang lasa", "Instant Noodles", {"safety"}, set()),
    # quantity and variant
    ("buy 1 take 1 pero isa lang ang dumating", "Shampoo 340ml", {"not_as_described"}, set()),
    ("I ordered black but they sent me a pink one instead", "Handheld Fan", {"not_as_described"}, set()),
    ("mali ang size na pinadala at iba ang kulay", "Dress for Women", {"not_as_described"}, set()),
    # multiple flags
    ("peke at sira agad, hindi gumana", "Power Bank 10000mAh", {"counterfeit", "defect"}, set()),
]


class RegressionMatrix(unittest.TestCase):
    def test_cases(self):
        for text, product, must, must_not in CASES:
            with self.subTest(text=text[:60], product=product):
                got = flags(text, product)
                self.assertTrue(must <= got, f"expected {sorted(must)} in {sorted(got)}")
                self.assertFalse(must_not & got, f"did not expect {sorted(must_not & got)}")

    def test_highlighted_spans_lie_inside_their_sentence_and_quote_real_characters(self):
        for text, product, must, _ in CASES:
            a = analyze(text, product)
            for sentence in a["sentences"]:
                raw = sentence["text_raw"]
                self.assertIn(raw.strip(), text, "a sentence must be a quote of the original review")
                for term in list(sentence.get("terms") or []) + list(sentence.get("extra_terms") or []):
                    span = term.get("span")
                    if term.get("excluded") or not span:
                        continue
                    self.assertTrue(0 <= span[0] < span[1] <= len(raw), (text, span, raw))
                    self.assertTrue(raw[span[0]:span[1]].strip(), (text, span))

    def test_a_flag_that_is_raised_for_a_clear_report_has_a_quotable_span(self):
        for text, product, must, _ in CASES:
            if not must:
                continue
            a = analyze(text, product)
            for flag in must:
                spans = [t for s in a["sentences"] for t in list(s.get("terms") or []) + list(s.get("extra_terms") or []) if t.get("category") == flag and not t.get("excluded") and t.get("span")]
                self.assertTrue(spans, f"{flag} in {text!r} has no highlighted span")


if __name__ == "__main__":
    unittest.main()
