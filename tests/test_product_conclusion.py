"""Product-specific conclusions: every reason on the card is a count of distinct reviews, with the words to prove it.

Covers the twenty cases of the panel brief, the evidence wording policy, and two regressions on the saved pool:
the explanation never changes a verdict or a decision, and every quotation and count can be traced to real reviews.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import aspects  # noqa: E402
import category_copy  # noqa: E402
import conclusion_text  # noqa: E402
import dashboard_utils as du  # noqa: E402
from aspect_profiles import EVIDENCE_POLICY  # noqa: E402

BASELINE = ROOT / "tests" / "fixtures" / "verdict_baseline_before_aspects.json"
SEED = ROOT / "backend" / "seed" / "saved_products.json.gz"


def reviews(texts, rating=5, start=0):
    return [{"comment_id": f"c{start + i}", "content": text, "rating": rating} for i, text in enumerate(texts)]


def summary(positive=80, uncertain=10, negative=10, bound=None):
    total = positive + uncertain + negative
    return {
        "sentiment_counts": {"positive": positive, "uncertain": uncertain, "negative": negative},
        "positive_ratio_lower_bound": bound if bound is not None else positive / total,
    }


def badges(safety=0, counterfeit=0, defect=0):
    return [{"category": "safety", "mentions": safety}, {"category": "counterfeit", "mentions": counterfeit}, {"category": "defect", "mentions": defect}]


def conclude(name, comments, state="no_warning_signs", data=None, found=None, usable=None, group=None):
    """The decision as dashboard_utils makes it, then explained from the reviews, exactly as the product page does."""
    data = data or summary()
    found = found or badges()
    usable = usable or len(comments)
    words = category_copy.profile(group)
    base = du._conclusion(data, state, found, usable, words)
    product = {"name": name, "link": f"https://example.test/{abs(hash(name))}-{len(comments)}", "comments": comments}
    return base, du._ground_conclusion(base, product, data, state, found, usable, words)


def text_of(conclusion):
    return f"{conclusion['lead']} {conclusion['summary']}"


class Cases(unittest.TestCase):
    # 1
    def test_positive_hair_reviews_name_what_customers_praised(self):
        texts = ["Ang lambot ng buhok ko pagkatapos gamitin", "My hair feels smoother after washing", "Sobrang bango at lambot", "Ang ganda ng amoy", "Mabango and soft talaga"] * 3
        base, out = conclude("Silka Shampoo 500ml", reviews(texts))
        self.assertEqual(out["decision"], base["decision"], "recommended")
        self.assertIn("softness", text_of(out))
        self.assertIn("fragrance", text_of(out))
        self.assertEqual(out["evidence_status"], "supported")

    # 2
    def test_negative_shampoo_reviews_name_the_complaints_not_praise(self):
        texts = ["Sobrang drying ng shampoo", "Nagdry buhok ko, ang drying", "Nangati anit ko", "drying talaga", "Hindi effective sa buhok ko"] * 3
        base, out = conclude("Silka Shampoo", reviews(texts, rating=1), data=summary(20, 10, 70))
        self.assertEqual(out["decision"], "not_recommended")
        self.assertIn("dryness", text_of(out))
        self.assertNotIn("praise", text_of(out).lower().replace("praised softness", ""))

    # 3
    def test_mixed_earbud_reviews_show_both_sides(self):
        good = ["Sound quality is great", "Ganda ng tunog", "Malinaw ang sound", "great sound", "maganda ang tunog"]
        bad = ["Nagdi-disconnect minsan", "disconnects often", "Hindi ma-connect", "connection issues", "laging disconnect"]
        base, out = conclude("TWS Wireless Earbuds", reviews(good + bad), data=summary(55, 15, 30, 0.5))
        self.assertEqual(out["decision"], "mixed")
        self.assertIn("sound quality", out["lead"])
        self.assertIn("Bluetooth connectivity", out["lead"])

    # 4
    def test_smartphone_battery_complaints(self):
        texts = ["Mahina ang battery", "Mabilis malowbat", "battery drains fast", "poor battery life", "Ang bilis maubos ng battery"]
        base, out = conclude("Samsung Galaxy A15 Phone 8GB", reviews(texts, rating=2), state="possible_counterfeit_or_defect", data=summary(40, 10, 50))
        self.assertIn("battery life", text_of(out))
        self.assertIn("problems with battery life", out["summary"])

    # 5
    def test_clothing_size_and_material_complaints(self):
        texts = ["Masyadong maliit ang size", "Too small, runs small", "Manipis ang tela", "see-through ang tela", "Hindi kasya sa akin", "sumikip agad"]
        base, out = conclude("Cotton T-shirt Oversized", reviews(texts, rating=2), data=summary(30, 10, 60))
        self.assertIn("fit and sizing", text_of(out))
        self.assertIn("fabric", text_of(out))

    # 6
    def test_food_freshness_complaints(self):
        texts = ["Panis na pagdating", "Stale na ang chips", "expired na", "Malapit na mag-expire", "may langgam sa loob", "Lipas na"]
        base, out = conclude("Crispy Chips Snack Pack", reviews(texts, rating=1), data=summary(25, 15, 60))
        self.assertIn("freshness", text_of(out))

    # 7
    def test_delivery_only_praise_does_not_make_the_product_praised(self):
        texts = ["Fast delivery", "Mabilis ang delivery", "Well packed", "Maayos ang packaging", "Fast shipping, thank you rider"] * 3
        base, out = conclude("Silka Shampoo", reviews(texts))
        self.assertEqual(out["decision"], base["decision"])
        self.assertEqual(out["evidence_status"], "limited")
        # The headline says what the reviews are about: delivery and packaging, "rather than how this hair product performs".
        self.assertIn("delivery and packaging rather than how this hair product performs", out["lead"])
        self.assertTrue(out["lead"].startswith("Although customer feedback is generally positive,"))
        self.assertNotRegex(text_of(out), r"praise[sd]? (?:softness|fragrance|performance)")
        self.assertNotRegex(text_of(out), r"well received")
        self.assertEqual(out["assessment_note"], "Limited product-specific feedback.")
        self.assertNotIn("customers praise", text_of(out).lower())

    def test_most_reviews_is_said_only_when_service_reviews_are_a_majority(self):
        """"Most reviews discuss delivery" needs >=10 reviews AND >=50% of the analyzed reviews; otherwise a weaker word."""
        product_reviews = ["Ang lambot ng buhok ko", "bango", "soft and smooth", "Mabango talaga", "Ang ganda ng amoy nya", "malambot ang buhok", "smooth hair", "Ang bango"]
        delivery = [f"Fast delivery po {n}" for n in range(30)]
        mixed = product_reviews * 1 + [f"Mabilis ang delivery {n}" for n in range(5)]
        _, few = conclude("Silka Shampoo", reviews(delivery[:6] + ["Ang lambot"]))
        _, majority = conclude("Silka Shampoo", reviews(delivery))
        self.assertNotIn("most reviews", few["lead"])
        self.assertIn("most reviews discuss delivery", majority["lead"])
        self.assertNotIn("most reviews", conclude("Silka Shampoo", reviews(mixed))[1]["lead"])

    # 8
    def test_empty_reviews_keep_the_plain_conclusion_without_inventing_reasons(self):
        for comments in ([], reviews(["", "  ", None])):
            base, out = conclude("Silka Shampoo", comments, usable=50)
            self.assertEqual(out, base)
            self.assertNotIn("evidence", out)
        self.assertIsNone(conclusion_text.compose(decision="recommended", state="no_warning_signs", usable=0, shares=None, mentions={}, result=aspects.extract([], None, None), noun="product", hazards=""))

    def test_too_few_reviews_show_no_percentage_even_with_aspect_evidence(self):
        base, out = conclude("Anker Charger", reviews(["Matibay", "Fast charging", "Sulit"]), state="insufficient_evidence", data=summary(3, 0, 0))
        self.assertEqual(out["decision"], "not_enough")
        self.assertNotIn("%", out["summary"])
        self.assertIn("Only 3 reviews could be analyzed", out["summary"])

    # 9
    def test_neutral_reviews_without_product_experience(self):
        texts = ["ok", "Received", "okay lang", "Nice", "thanks", "ok po"] * 2
        base, out = conclude("Silka Shampoo", reviews(texts), data=summary(30, 60, 10, 0.2))
        self.assertEqual(out["evidence_status"], "limited")
        self.assertEqual(out["evidence"]["why"], [])
        self.assertNotRegex(text_of(out), r"praise|softness|fragrance|battery")

    # 10
    def test_conflicting_opinions_are_reported_as_a_disagreement(self):
        texts = ["Ang lambot ng buhok", "soft and smooth", "malambot talaga", "lambot", "sobrang soft"] + ["Hindi malambot", "not soft at all", "matigas ang buhok", "rough hair", "magaspang"]
        base, out = conclude("Silka Shampoo", reviews(texts), data=summary(55, 15, 30, 0.5))
        self.assertIn("disagree about softness", out["summary"])
        self.assertNotIn("praised softness", out["summary"])
        self.assertNotIn("praise softness", out["lead"])

    # 11
    def test_counterfeit_denials_are_not_counterfeit_complaints(self):
        texts = ["Hindi naman fake, original talaga", "Not fake, legit", "I thought it was fake, but it is genuine", "hindi peke, orig"]
        result = aspects.extract(reviews(texts), None, None)
        row = next(r for r in result["aspects"] if r["id"] == "authenticity")
        self.assertEqual((row["positive"]["reviews"], row["negative"]["reviews"]), (4, 0))
        base, out = conclude("Anker Charger", reviews(texts * 2))
        self.assertNotIn("question whether", out["summary"])

    # 12
    def test_safety_reports_stay_visible_and_are_worded_as_reports(self):
        texts = ["Sobrang lambot ng buhok"] * 1 + ["Nag-overheat at umusok yung charger", "Umusok", "Mainit na mainit"]
        base, out = conclude("Silka Shampoo", reviews(texts * 3), state="possible_safety_issue", data=summary(80, 10, 10, 0.75), found=badges(safety=2))
        self.assertEqual(out["decision"], "caution")
        self.assertIn("2 reviews describe a possible safety problem", out["summary"])
        self.assertNotRegex(text_of(out), r"\b(?:is|are) (?:safe|unsafe|dangerous)\b|(?<!not been )independent(?:ly)? (?:verified|confirmed)")
        # the report is shown as unverified, and the warning is its own field so the card can set it apart (and never fold it away)
        self.assertEqual(out["warnings"], [s for s in out["warnings"] if "not been independently verified" in s])
        self.assertEqual(len(out["warnings"]), 1)
        self.assertIn(out["warnings"][0], out["summary"])
        self.assertNotIn(out["warnings"][0], out["body"])

    # 13
    def test_favorable_sentiment_cannot_hide_a_safety_warning(self):
        texts = ["Ang lambot ng buhok", "bango", "soft"] * 5 + ["Nag-apoy ang charger"]
        base, out = conclude("Silka Shampoo", reviews(texts), state="safety_warning", data=summary(95, 3, 2, 0.9), found=badges(safety=3))
        self.assertEqual(out["decision"], "not_recommended")
        self.assertIn("3 reviews describe a possible safety problem", out["summary"])
        self.assertIn("possible safety problems", out["lead"])
        self.assertNotIn("favorable", out["lead"])

    # 14
    def test_repeated_reviews_count_once(self):
        same = ["Ang lambot ng buhok ko"] * 10
        result = aspects.extract(reviews(same), "haircare", None)
        row = next(r for r in result["aspects"] if r["id"] == "softness")
        self.assertEqual(row["positive"]["reviews"], 1)
        self.assertEqual(result["skipped_clauses"]["duplicate_text"], 9)
        flagged = reviews(["Ang lambot ng buhok", "Ang lambot ng buhok nya"])
        flagged[1]["is_duplicate"] = True
        self.assertEqual(next(r for r in aspects.extract(flagged, "haircare", None)["aspects"] if r["id"] == "softness")["positive"]["reviews"], 1)

    def test_one_review_never_counts_twice_for_one_aspect(self):
        result = aspects.extract(reviews(["Malambot ang buhok, ang lambot talaga, soft soft soft"]), "haircare", None)
        row = next(r for r in result["aspects"] if r["id"] == "softness")
        self.assertEqual(row["positive"]["reviews"], 1)
        self.assertEqual(len(row["positive"]["review_ids"]), 1)

    def test_a_review_that_praises_and_criticises_one_aspect_counts_for_neither(self):
        result = aspects.extract(reviews(["Malambot sa una. Ngayon hindi malambot na"]), "haircare", None)
        row = next(r for r in result["aspects"] if r["id"] == "softness")
        self.assertEqual((row["positive"]["reviews"], row["negative"]["reviews"], row["mixed_reviews"]), (0, 0, 1))

    # 15
    def test_missing_category_uses_general_aspects(self):
        base, out = conclude("", reviews(["Matibay at ganda ng quality", "Sulit na sulit", "Good quality", "worth the price", "sulit"] * 2))
        text = text_of(out)
        self.assertTrue("build quality" in text or "value for money" in text)
        self.assertEqual(aspects.profiles.profile_key(None, None), "general")

    # 16
    def test_filipino_and_taglish_negation(self):
        def one(text, category="haircare"):
            result = aspects.extract(reviews([text]), category, None)
            return {r["id"]: ("positive" if r["positive"]["reviews"] else "negative") for r in result["aspects"]}

        self.assertEqual(one("Hindi malambot")["softness"], "negative")
        self.assertEqual(one("not soft")["softness"], "negative")
        self.assertEqual(one("Malambot")["softness"], "positive")
        self.assertNotIn("dryness", one("Hindi naman drying"))  # a denied problem is not a complaint
        self.assertNotIn("dryness", one("Walang drying sa buhok ko"))
        self.assertEqual(one("Hindi effective sa buhok ko")["functionality"], "negative")
        self.assertEqual(one("not bad"), {})
        self.assertEqual(one("Ang ganda ng amoy pero sobrang drying"), {"fragrance": "positive", "dryness": "negative"})
        self.assertEqual(one("Fast delivery pero hindi gumagana", None)["delivery"], "positive")
        self.assertEqual(one("Fast delivery pero hindi gumagana", None)["functionality"], "negative")
        self.assertEqual(one("Okay naman yung shampoo, pero nangati anit ko"), {"scalp_irritation": "negative"})
        self.assertEqual(one("akala ko fake pero original talaga", None), {"authenticity": "positive"})

    def test_not_used_yet_reviews_cannot_praise_performance(self):
        result = aspects.extract(reviews(["Five stars muna, hindi ko pa natry, sana maganda", "Hindi ko pa nagamit pero ang bango"]), "haircare", None)
        self.assertEqual(sum(r["positive"]["reviews"] for r in result["aspects"] if r["kind"] == "product"), 0)

    def test_comparisons_and_sarcasm_are_skipped(self):
        result = aspects.extract(reviews(["Mas malambot kaysa sa dati", "better than my old one, soft", "ganda ng amoy 😡"]), "haircare", None)
        self.assertEqual(result["aspects"], [])
        self.assertGreaterEqual(result["skipped_clauses"]["comparison"], 2)

    def test_praise_in_a_one_star_review_is_set_aside(self):
        result = aspects.extract(reviews(["Ang lambot ng buhok"], rating=1), "haircare", None)
        self.assertEqual(result["aspects"], [])

    def test_menu_tag_blocks_are_not_endorsements(self):
        blob = "Excellent build quality., Great value for money., Perfect length for my setup., Sleek and professional design."
        result = aspects.extract(reviews([blob, blob + " Fast", blob + " Thanks", blob + " Okay"]), None, None)
        self.assertEqual(result["aspects"], [])
        self.assertEqual(result["skipped_clauses"]["menu_tag"], 4)

    # 17
    def test_the_percentage_wording_bug(self):
        shares = {"positive": 0.25, "uncertain": 0.65, "negative": 0.10}
        sentence = conclusion_text.mood_sentence(shares, 100)
        self.assertNotIn("mostly negative", sentence)
        self.assertIn("25%", sentence)
        self.assertIn("65%", sentence)
        self.assertIn("neutral or did not express a clear opinion", sentence)
        self.assertEqual(conclusion_text.feeling(shares), "mostly neutral or unclear")
        # the plain (no review text) card says the same thing and does not call it negative
        base = du._conclusion(summary(25, 65, 10, 0.2), "no_warning_signs", badges(), 100)
        self.assertEqual(base["decision"], "not_recommended", "decision thresholds are untouched")
        self.assertNotIn("mostly negative", base["summary"])
        self.assertNotIn("most reviewers were negative", base["text"])
        self.assertNotIn("Most reviewers were unhappy", base["assessment_note"])
        self.assertIn("neutral", base["summary"])

    def test_a_real_negative_majority_is_still_called_negative(self):
        self.assertEqual(conclusion_text.feeling({"positive": 0.2, "uncertain": 0.2, "negative": 0.6}), "mostly negative")
        self.assertIn("negative", conclusion_text.mood_sentence({"positive": 0.2, "uncertain": 0.2, "negative": 0.6}, 50))
        base = du._conclusion(summary(20, 20, 60, 0.2), "no_warning_signs", badges(), 100)
        self.assertEqual(base["assessment_note"], "Most reviewers were unhappy or reported serious problems.")

    def test_percentages_add_up_to_one_hundred(self):
        for shares in ({"positive": 1 / 3, "uncertain": 1 / 3, "negative": 1 / 3}, {"positive": 0.505, "uncertain": 0.495, "negative": 0.0}):
            self.assertEqual(sum(conclusion_text.percents(shares)), 100)

    # 18
    def test_missing_or_incomplete_review_data_never_breaks_the_card(self):
        comments = [{"content": "Ang lambot ng buhok"}, {"comment_id": None, "content": "bango", "rating": None}, {"rating": 5}, None, "text", {"content": 123}]
        result = aspects.extract(comments, "haircare", None)
        ids = [rid for row in result["aspects"] for side in ("positive", "negative") for rid in row[side]["review_ids"]]
        self.assertEqual(len(ids), len(set(ids)) or 0 + len(ids))
        base, out = conclude("Silka Shampoo", comments, usable=10)
        self.assertEqual(out["decision"], base["decision"])

    # 19
    def test_reasons_the_reviews_do_not_support_are_never_written(self):
        texts = ["Ok naman", "Maayos", "Salamat po", "Good", "Fast delivery"] * 4
        base, out = conclude("Silka Shampoo", reviews(texts))
        for invented in ("softness", "fragrance", "dryness", "irritation", "manageab", "battery", "sound"):
            self.assertNotIn(invented, text_of(out).lower())

    def test_aspects_supported_only_by_negative_reviews_are_not_praised(self):
        texts = ["Hindi malambot", "Matigas ang buhok", "not soft", "magaspang"] * 2
        base, out = conclude("Silka Shampoo", reviews(texts, rating=2), data=summary(80, 10, 10, 0.75))
        self.assertNotIn("praised softness", out["summary"])
        self.assertNotIn("for softness", out["lead"])

    # 20
    def test_a_very_long_product_name_cannot_enter_or_lengthen_the_card(self):
        name = "【Best-Selling】 Premium Moisturizing Shampoo " + "Super Long Product Name " * 40
        texts = ["Ang lambot ng buhok", "bango", "soft", "mabango", "lambot"] * 3
        base, out = conclude(name, reviews(texts))
        self.assertNotIn("Super Long", text_of(out))
        self.assertLessEqual(len(text_of(out).split()), EVIDENCE_POLICY["target_words"])


# One real-sounding sentence per aspect, in the product type that reads it. If a table is edited and an aspect stops
# matching its own example (a bad escape, a typo), this fails by name. It guards the failure that hid the seller aspect.
EXAMPLES = {
    "functionality": (None, "Hindi gumagana", "negative"),
    "build": (None, "Poor quality", "negative"),
    "durability": (None, "Nasira agad after 2 weeks", "negative"),
    "size": (None, "Masyadong maliit", "negative"),
    "appearance": (None, "Maganda ang design", "positive"),
    "value": (None, "Sayang pera", "negative"),
    "ease": (None, "Easy to use", "positive"),
    "matches_listing": (None, "Wrong item ang dumating", "negative"),
    "authenticity": (None, "Hindi original", "negative"),
    "delivery": (None, "Mabilis ang delivery", "positive"),
    "packaging": (None, "Maayos ang packaging", "positive"),
    "seller": (None, "Rude ang seller", "negative"),
    "freebies": (None, "Walang freebie", "negative"),
    "arrival": (None, "Dumating na sira ang item", "negative"),
    "softness": ("haircare", "Ang lambot ng buhok", "positive"),
    "manageability": ("haircare", "Madaling suklayin", "positive"),
    "fragrance": ("haircare", "Ang bango", "positive"),
    "gentleness": ("skincare", "Gentle on the skin", "positive"),
    "dryness": ("haircare", "Sobrang drying", "negative"),
    "scalp_irritation": ("haircare", "Nangati anit ko", "negative"),
    "hair_fall": ("haircare", "Nalagas ang buhok ko", "negative"),
    "texture": ("skincare", "Malagkit", "negative"),
    "absorption": ("skincare", "Mabilis sumipsip", "positive"),
    "oiliness": ("skincare", "Sobrang oily", "negative"),
    "skin_irritation": ("skincare", "Nagka-pimples ako", "negative"),
    "battery": ("phone", "Mahina ang battery", "negative"),
    "camera": ("phone", "Maganda ang camera", "positive"),
    "performance": ("phone", "Smooth ang takbo", "positive"),
    "charging": ("phone", "Fast charging", "positive"),
    "display": ("phone", "Clear ang screen", "positive"),
    "overheating": ("phone", "Umiinit agad", "negative"),
    "shutdowns": ("powerbank", "Biglang namatay", "negative"),
    "sound": ("audio", "Ganda ng tunog", "positive"),
    "comfort": ("audio", "Comfortable sa tenga", "positive"),
    "connectivity": ("audio", "Nagdi-disconnect", "negative"),
    "microphone": ("audio", "Mic not working", "negative"),
    "capacity": ("powerbank", "Isang charge lang", "negative"),
    "fabric": ("apparel", "Manipis ang tela", "negative"),
    "stitching": ("apparel", "Natastas ang tahi", "negative"),
    "material": ("footwear", "Cheap ang material", "negative"),
    "taste": ("food_beverage", "Masarap", "positive"),
    "freshness": ("food_beverage", "Panis na", "negative"),
    "expiry": ("food_beverage", "Expired na", "negative"),
    "quantity": ("food_beverage", "Kaunti ang laman", "negative"),
    "mixability": ("health_supplements", "Poor mixability", "negative"),
    "noise": ("small_appliance", "Maingay", "negative"),
    "power_use": ("small_appliance", "Tipid sa kuryente", "positive"),
    "fitment": ("motorcycle", "Hindi kasya", "negative"),
    "storage": ("bags", "Very spacious", "positive"),
    "zipper": ("bags", "Sira ang zipper", "negative"),
}


class PatternIntegrity(unittest.TestCase):
    def test_no_pattern_contains_a_control_character(self):
        import aspect_profiles as ap

        bad = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")
        seen = set()
        for key in ap.PROFILES:
            for aspect in ap.aspects_for({"hair": "haircare", "general": None}.get(key, key), None):
                for pattern in aspect.pos + aspect.neg + aspect.topic:
                    seen.add(pattern.pattern)
        for name in ("HYPOTHETICAL", "COMPARISON", "SARCASM", "NO_EXPERIENCE", "RELIEF", "HABIT", "PROMOTION", "PROMPT_LABEL"):
            seen.add(getattr(ap, name).pattern)
        for name in ("MENU_TAGS", "_MENU_COMMAS", "_MENU_LABELLED", "_MENU_TRAILING", "_MENU_MIDWORD", "_FIRST_PERSON", "_STRETCH"):
            seen.add(getattr(aspects, name).pattern)
        self.assertGreater(len(seen), 200)
        self.assertEqual([p for p in seen if bad.search(p)], [])

    def test_every_aspect_matches_its_own_example(self):
        import aspect_profiles as ap

        every = {a.id for key in ap.PROFILES for a in ap.aspects_for({"hair": "haircare", "skin": "skincare", "earbuds": "audio", "appliance": "small_appliance", "motorcycle": "motorcycle", "food": "food_beverage", "general": None}.get(key, key), None)}
        self.assertEqual(sorted(every - set(EXAMPLES)), [], "an aspect without an example")
        failures = []
        for aspect_id, (category, text, polarity) in EXAMPLES.items():
            result = aspects.extract(reviews([text]), category, None)
            row = next((r for r in result["aspects"] if r["id"] == aspect_id), None)
            if row is None or not row[polarity]["reviews"]:
                failures.append((aspect_id, text))
        self.assertEqual(failures, [])

    def test_stretched_letters_are_cut_back(self):
        self.assertEqual(aspects.fold("Gandaaaa ng amoy, gooood"), "ganda ng amoy, good")

    def test_the_first_product_page_does_not_load_the_sentiment_models(self):
        """Cold start: reading reviews must not import numpy, scikit-learn or the models (about 7 s on a fast PC)."""
        script = (
            "import sys, time, json\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "t = time.perf_counter()\n"
            "import aspects\n"
            "aspects.extract([{'comment_id': '1', 'content': 'Ang lambot ng buhok, hindi gumagana ang pump', 'rating': 5}], 'haircare', None)\n"
            "print(json.dumps({'seconds': time.perf_counter() - t, 'heavy': [m for m in ('numpy', 'sklearn', 'joblib', 'onnxruntime') if m in sys.modules]}))\n"
        )
        import subprocess

        ran = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT / "backend")], capture_output=True, text=True)
        self.assertEqual(ran.returncode, 0, ran.stderr[-600:])
        out = json.loads(ran.stdout)
        self.assertEqual(out["heavy"], [])
        self.assertLess(out["seconds"], 3.0)

    def test_the_standalone_segmenter_cuts_exactly_like_the_package_one(self):
        sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
        from defaketive_sentiment import text_norm as package

        standalone = aspects._normalizer()
        self.assertEqual((standalone.NORMALIZER_VERSION, standalone.SEGMENTER_VERSION), (package.NORMALIZER_VERSION, package.SEGMENTER_VERSION))
        for text in ("Ang ganda ng amoy pero sobrang drying.", "I thought it was fake, but it is genuine \U0001F60D\U0001F44D", "Okay naman yung shampoo, pero nangati anit ko", "a\nb\n\n" * 5):
            self.assertEqual(standalone.segment_sentences(text), package.segment_sentences(text))


class Policy(unittest.TestCase):
    def test_evidence_words_follow_the_configured_tiers(self):
        self.assertEqual([aspects.tier_word(n) for n in (1, 2, 3, 4, 9, 10, 40)], ["one", "some", "some", "several", "several", "many", "many"])

    def test_most_needs_a_real_majority_of_a_real_sample(self):
        self.assertEqual(aspects.tier_word(6, 10), "several")  # 60% of ten reviews is not "most"
        self.assertEqual(aspects.tier_word(12, 20), "most")
        self.assertEqual(aspects.tier_word(12, 100), "many")

    def test_one_mention_is_worded_as_one_reviewer(self):
        row = {"label": "fragrance", "positive": {"reviews": 1}}
        self.assertEqual(conclusion_text.praise_sentence([row], 50, 3), "One reviewer praised fragrance.")

    def test_thresholds_can_be_changed_without_touching_code(self):
        self.assertTrue(set(EVIDENCE_POLICY) >= {"tiers", "lead_min_reviews", "contested_ratio", "limited_min_reviews", "most_share"})

    def test_new_aspects_are_added_by_data(self):
        import re as _re

        from aspect_profiles import Aspect, _re as compile_all

        extra = Aspect("packaging_scent", "scent of the box", pos=compile_all([r"\bamoy\s+ng\s+box\b"]))
        self.assertEqual(extra.label, "scent of the box")
        self.assertTrue(extra.quick.search("ang amoy ng box"))


class Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = [item["product"] for item in json.load(gzip.open(SEED, "rt", encoding="utf-8"))]
        cls.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_the_explanation_changes_no_verdict_and_no_decision(self):
        swap = re.compile(r"most reviewers were not happy|most reviewers were negative|few reviewers were positive")
        for product in self.products:
            plain, grounded = du.badge_view(product), du.badge_view(product, aspects=True)
            before = self.baseline[product["link"]]
            for key in ("state", "tone", "headline", "counts"):
                self.assertEqual(plain[key], before[key], key)
                self.assertEqual(grounded[key], before[key], key)
            c = grounded["conclusion"]
            self.assertEqual((c or {}).get("decision"), before["decision"], product["name"])
            self.assertEqual((c or {}).get("headline"), before["conclusion_headline"])
            self.assertEqual((c or {}).get("basis"), before["basis"])
            if c:
                self.assertEqual(swap.sub("<u>", c["text"]), swap.sub("<u>", before["text"]))
                self.assertEqual(plain["conclusion"]["decision"], c["decision"])
                self.assertEqual(plain["badges"], grounded["badges"])

    def test_every_displayed_claim_traces_to_real_reviews(self):
        checked = 0
        for product in self.products:
            c = du.badge_view(product, aspects=True)["conclusion"]
            if not c or "evidence" not in c:
                continue
            by_id = {f"review-{i}": x for i, x in enumerate(product["comments"])} | {str(x["comment_id"]): x for x in product["comments"] if x.get("comment_id")}
            for item in c["evidence"]["why"]:
                self.assertGreaterEqual(item["reviews"], 1)
                self.assertEqual(len(item["review_ids"]), len(set(item["review_ids"])), "a review is listed once")
                self.assertEqual(len(item["review_ids"]), min(item["reviews"], EVIDENCE_POLICY["ids_per_side"]))
                self.assertTrue(item["quotes"], "a count without a quotation is not shown")
                for rid in item["review_ids"]:
                    self.assertIn(rid, by_id)
                for quote in item["quotes"]:
                    raw = str(by_id[quote["review_id"]]["content"])
                    content = " ".join(raw.split())
                    text = quote["text"]
                    cut = text.endswith("…") and " ".join(raw[quote["span"][0] : quote["span"][1]].split()) != text if quote["span"] else False
                    shown = text[:-1] if cut else text  # the ellipsis is ours only when the slice is shorter than the text
                    self.assertIn(shown.rstrip(), content)
                    if quote["span"]:
                        self.assertEqual(" ".join(raw[quote["span"][0] : quote["span"][1]].split()), shown.rstrip())
                    checked += 1
        self.assertGreater(checked, 3000)

    def test_counts_are_reproducible_and_deterministic(self):
        product = max(self.products, key=lambda p: len(p["comments"]))
        group = du.product_group(product)
        category = du.product_category_of(product)
        one = aspects.extract(product["comments"], category, group)
        two = aspects.extract(list(reversed(product["comments"])), category, group)
        counts = lambda r: {(row["id"], side): row[side]["reviews"] for row in r["aspects"] for side in ("positive", "negative")}
        self.assertEqual(one, aspects.extract(product["comments"], category, group))
        self.assertEqual(sum(counts(one).values()) > 0, True)
        # order of reviews may change which duplicate is kept, but never a count by more than the duplicates removed
        for key, value in counts(one).items():
            self.assertLessEqual(abs(value - counts(two).get(key, 0)), 2)

    def test_the_conclusion_is_short_enough_for_a_phone(self):
        longest = 0
        for product in self.products:
            c = du.badge_view(product, aspects=True)["conclusion"]
            if c:
                longest = max(longest, len(text_of(c).split()))
        self.assertLessEqual(longest, EVIDENCE_POLICY["target_words"])

    def test_a_saved_report_without_review_text_falls_back_without_inventing(self):
        product = {k: v for k, v in self.products[0].items() if k != "comments"}
        view = du.badge_view(product, aspects=True)
        self.assertNotIn("evidence", view["conclusion"])
        self.assertEqual(view["conclusion"]["decision"], self.baseline[product["link"]]["decision"])

    def test_the_environment_variable_switches_the_feature_in_a_fresh_process(self):
        """DEFAKETIVE_CONCLUSION_REASONS is read at start. Run the real module in separate processes, with it on, off and unset."""
        import os
        import subprocess

        script = (
            "import gzip, json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import dashboard_utils as du\n"
            "p = json.load(gzip.open(sys.argv[2], 'rt', encoding='utf-8'))[0]['product']\n"
            "c = du.badge_view(p, aspects=True)['conclusion']\n"
            "print(json.dumps({'enabled': du.REASONS_ENABLED, 'has_evidence': 'evidence' in c, 'decision': c['decision'], 'headline': c['headline'], 'has_text': bool(c['text'] and c['summary'] and c['lead'])}))\n"
        )
        results = {}
        for label, value in (("unset", None), ("on", "1"), ("off", "0"), ("off_word", "off")):
            env = {k: v for k, v in os.environ.items() if k != "DEFAKETIVE_CONCLUSION_REASONS"}
            if value is not None:
                env["DEFAKETIVE_CONCLUSION_REASONS"] = value
            ran = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT / "backend"), str(SEED)], capture_output=True, text=True, env=env)
            self.assertEqual(ran.returncode, 0, ran.stderr[-500:])
            results[label] = json.loads(ran.stdout)
        self.assertTrue(results["unset"]["has_evidence"] and results["on"]["has_evidence"], "on by default")
        self.assertFalse(results["off"]["has_evidence"] or results["off_word"]["has_evidence"])
        self.assertTrue(all(r["has_text"] for r in results.values()), "the original conclusion is intact when it is off")
        self.assertEqual({r["decision"] for r in results.values()}, {results["on"]["decision"]}, "the decision is the same on and off")
        self.assertEqual({r["headline"] for r in results.values()}, {results["on"]["headline"]})

    def test_rollback_needs_no_migration_because_nothing_is_stored_or_changed(self):
        """Conclusions are computed when a page opens. Producing one must not change the saved report, so removing the feature leaves no trace."""
        import copy

        for product in self.products[:25]:
            before = copy.deepcopy(product)
            du.badge_view(product, aspects=True)
            du.with_badge_view(product, aspects=True)
            self.assertEqual(product, before, product["name"])
        # and the module stores nothing on disk: its only state is an in-memory cache
        import inspect

        source = inspect.getsource(aspects) + inspect.getsource(conclusion_text)
        for forbidden in ("open(", "sqlite3", ".write(", "json.dump(", "Path.write"):
            self.assertNotIn(forbidden, source, forbidden)

    def test_the_off_switch_returns_every_page_to_the_plain_conclusion(self):
        product = self.products[0]
        on = du.badge_view(product, aspects=True)["conclusion"]
        self.assertIn("evidence", on)
        du.REASONS_ENABLED = False
        try:
            off = du.badge_view(product, aspects=True)["conclusion"]
        finally:
            du.REASONS_ENABLED = True
        self.assertNotIn("evidence", off)
        self.assertNotIn("warnings", off)
        self.assertEqual(off, du.badge_view(product)["conclusion"], "off means exactly the list-view conclusion")
        for key in ("decision", "headline", "basis", "points", "notice"):
            self.assertEqual(off[key], on[key], key)

    def test_extraction_is_fast_and_cached(self):
        product = max(self.products, key=lambda p: len(p["comments"]))
        aspects.clear_cache()
        start = time.perf_counter()
        first = aspects.cached_extract(product["link"], product["comments"], du.product_category_of(product), du.product_group(product))
        cold = time.perf_counter() - start
        start = time.perf_counter()
        again = aspects.cached_extract(product["link"], product["comments"], du.product_category_of(product), du.product_group(product))
        warm = time.perf_counter() - start
        self.assertIs(first, again)
        self.assertLess(cold, 2.0)
        self.assertLess(warm, 0.05)


# Claims the card must never make. Each pattern is a thing an overconfident summary would say.
FORBIDDEN = re.compile(
    r"\b(?:is|are|looks?|seems?)\s+(?:completely\s+|totally\s+)?(?:safe|unsafe|dangerous|harmless)\b"
    r"|\bsafe to use\b|(?<!whether the product )(?<!whether it )(?<!whether they )\b(?:is|are)\s+(?:genuine|authentic|counterfeit|fake)\b"
    r"|\b(?:all|every|everyone|everybody|no one|nobody)\s+(?:customers?|reviewers?|buyers?|people)\b"
    r"|\bguarantee[sd]?\b|\bproven\b|(?<!not been independently )\bverified\b(?!\s+(?:purchase|buyer))|\bmost customers\b"
    r"|\bhair growth\b|\bcures?\b",
    re.I,
)


class Wording(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = [item["product"] for item in json.load(gzip.open(SEED, "rt", encoding="utf-8"))]

    def test_no_generated_text_on_any_saved_product_makes_a_forbidden_claim(self):
        for product in self.products:
            c = du.badge_view(product, aspects=True)["conclusion"]
            if c:
                self.assertIsNone(FORBIDDEN.search(text_of(c)), (product["name"], text_of(c)))

    def test_most_is_only_said_with_a_majority_behind_it(self):
        for product in self.products:
            c = du.badge_view(product, aspects=True)["conclusion"]
            if not c:
                continue
            text = text_of(c)
            shares = du._sentiment_shares(product["sentiment_summary"]) or {}
            if re.search(r"mostly negative|most reviewers were negative|most reviewers were not happy", text):
                self.assertGreater(shares.get("negative", 0), 0.5, product["name"])
            if re.search(r"most reviews \(\d+%\)", text):
                self.assertGreaterEqual(shares.get("uncertain", 0), 0.5, product["name"])
            for match in re.finditer(r"\bMost reviewers (?:praised|reported)\b", text):
                self.fail(f"'Most reviewers' is a sentence about distinct-review shares and needs >=50% of the sample: {product['name']}")

    def test_every_headline_begins_with_its_basis(self):
        for product in self.products:
            c = du.badge_view(product, aspects=True)["conclusion"]
            if c and "evidence" in c:
                self.assertTrue(c["lead"].startswith(("Based on customer reviews", "Although customer feedback")), c["lead"])

    def test_recurring_authenticity_doubts_are_worded_as_questions_not_findings(self):
        texts = ["Fake daw ito", "Hindi original", "peke ang charger", "Not original", "Fake"] + ["Fast charging", "Sulit", "Ang bilis mag-charge"] * 3
        _, out = conclude("Anker Charger", reviews(texts), state="possible_counterfeit_or_defect", data=summary(60, 10, 30, 0.5), found=badges(counterfeit=5))
        self.assertIn("5 reviews question whether the product is genuine", out["summary"])
        self.assertIsNone(FORBIDDEN.search(text_of(out)))
        self.assertIn("doubts about authenticity", out["lead"])

    def test_packaging_only_reviews_say_so(self):
        texts = ["Well packed", "Maayos ang packaging", "Secure packaging", "Bubble wrap ang balot", "Well packaged po"] * 3
        _, out = conclude("Silka Shampoo", reviews(texts))
        self.assertEqual(out["evidence_status"], "limited")
        self.assertIn("packaging rather than how this hair product performs", out["lead"])
        self.assertNotIn("delivery", out["lead"])

    def test_every_error_found_on_real_reviews_stays_fixed(self):
        """Each input below is a real review sentence from the project's own scans that the first version read wrongly."""

        def claims(category, text):
            result = aspects.extract(reviews([text]), category, None)
            return {r["id"]: ("positive" if r["positive"]["reviews"] else "negative") for r in result["aspects"] if r["positive"]["reviews"] or r["negative"]["reviews"]}

        cases = [
            ("skincare", "Gentle on the skin, does not irritate or cause any breakouts, and does not sting when applied.", {"gentleness": "positive"}),  # "not X or Y"
            ("skincare", "It really suits sensitive and acne-prone skin.", {}),  # the skin it is for
            ("skincare", "Highly recommended when you have sensitive or acne prone skin.", {}),
            ("skincare", "it's my first time to try Cetaphil gentle skin cleanser", {}),  # a product name
            ("skincare", "Effectiveness:Reduces acne", {}),  # what it treats
            ("skincare", "May napansin lang ako, bakit as shown sa video tinakpan yung barcode.", {}),  # "as shown" is a complaint here
            ("skincare", "so far bet ko sya smoooth sa balat hndi malagkit!", {"texture": "positive"}),  # "hndi" is "hindi"
            ("skincare", "kahit di pa nagagamit yung 1st bottle", {}),  # not used yet
            ("food_beverage", "Effectiveness:legit", {}),  # the answer belongs to its prompt
            ("food_beverage", "Their website was user-friendly, making it easy to find the perfect item.", {}),  # the shop's website
            ("food_beverage", "not exactly gamot pro nakakatulong", {"functionality": "positive"}),  # "pro" is "pero"
            ("haircare", "This shampoo deeply moisturizes and nourishes dry hair leaving it soft and manageable.", {"softness": "positive", "manageability": "positive"}),
            ("haircare", "Generally effective for mild to moderately dry hair", {"functionality": "positive"}),
            ("haircare", "Leaves a pleasant and long-lasting fragrance", {}),  # not durability
            ("haircare", "thanks seller at kay kuya rider receive ko na po yng items kya lng sira sira na ang box ng dumating", {"packaging": "negative"}),  # the box, not whether it works
            ("haircare", "Fragrance: sakto lang di overpowering ang bango.", {"fragrance": "positive"}),
            ("haircare", "Effective in smoothening the frizzy, dry hair.", None),  # known open case: recorded in aspect_validation.md, not asserted
            ("skincare", "Ang laki ng sayang.", {}),  # not about size
            ("food_beverage", "wow almost half the price laki ng tipid.", {}),
            # Round 3: found by reading the conclusions of products NOT used to write the rules (an anti-hair-fall shampoo, an antiseptic cleanser)
            ("haircare", "I've noticed less hairfall in and out of the shower.", {}),  # praise that names the problem it lessens
            ("haircare", "Mas less ang hair fall kapag ito ginagamit ko.", {}),
            ("haircare", "I've been using hosku for a year now and it is so effective in helping with hair fall.", {"functionality": "positive"}),  # praise of the effect, and NO hair_fall complaint
            ("haircare", "Excellent for daily hair care & anti-hair loss", {}),
            ("haircare", "It made my hair fall more. Nagpa has buhos ko dito.", {"hair_fall": "negative"}),  # a real complaint is still one
            ("haircare", "I'm still experiencing hair fall and a bunch of it.", {"hair_fall": "negative"}),
            ("skincare", "pero at least hindu nangangati yung scalp ko despite continuous use..", {}),  # "hindu" is "hindi"
            ("skincare", "For my rashes, I still use topical steroid cream", {}),  # the problem the buyer already had
            ("skincare", "as some people may experience skin irritation or allergic reaction", {}),  # what could happen
            ("skincare", "Pag natuyo at tumagal mapapansin mong nag leave sya ng white stain", {}),  # the product dried
            ("skincare", "maganda ,malambot sa face non greasy pa", {}),  # "non greasy" is praise
            ("skincare", "nag allergy balat ko, kaya tinigil ko na ang pag gamit.", {"skin_irritation": "negative"}),
            ("skincare", "Nakakatuyo ng balat ko", {"dryness": "negative"}),
        ]
        wrong = []
        for category, text, expected in cases:
            if expected is None:
                continue
            got = claims(category, text)
            if got != expected and not (expected and set(expected.items()) <= set(got.items()) and all(k in expected or k in ("functionality", "gentleness", "value", "seller", "build") for k in got)):
                wrong.append((text[:60], got, expected))
        self.assertEqual(wrong, [])

    def test_food_and_beauty_say_overall_quality_not_build_quality(self):
        for category in ("food_beverage", "haircare", "skincare"):
            result = aspects.extract(reviews(["Good quality po talaga"]), category, None)
            build = next(r for r in result["aspects"] if r["id"] == "build")
            self.assertEqual(build["label"], "overall quality")
            self.assertNotIn("durability", {a.id for a in aspects.profiles.aspects_for(category, None)})

    def test_a_headline_never_lists_the_same_problem_twice_or_more_than_three_reasons(self):
        """Found by the quality audit: "defects" (hazard checker) plus "faults or failure to work" (an aspect) in one headline."""
        broken = ["Hindi gumagana", "Sira agad", "Defective item", "Hindi gumagana ang charger", "Nasira after 1 week", "Sira na pagdating"] * 2
        listing = ["Wrong item ang dumating", "Mali ang kulay", "Wrong size", "Kulang ang laman"] * 2
        texts = broken + listing + ["Overheat", "Umiinit sobra"] * 2 + ["Mahina ang battery", "Bad battery life"] * 2
        _, out = conclude("Anker Power Bank", reviews(texts), state="possible_safety_issue", data=summary(75, 10, 15, 0.7), found=badges(safety=2, defect=5, counterfeit=3))
        lead = out["lead"]
        self.assertIn("defects", lead)
        self.assertNotIn("faults or failure to work", lead, "the same problem is not named twice")
        self.assertNotIn("some reviewers report", lead, "a headline names no quantity it has not counted")
        reasons = lead.split("reports of ", 1)[1].rstrip(".")
        self.assertLessEqual(len(re.split(r", | and ", reasons)), 6, "a headline is a sentence, not a list")
        self.assertLessEqual(len(lead.split()), 40)

    def test_english_negation(self):
        def one(text, category="haircare"):
            result = aspects.extract(reviews([text]), category, None)
            return {r["id"]: ("positive" if r["positive"]["reviews"] else "negative") for r in result["aspects"]}

        self.assertEqual(one("It is not effective for me")["functionality"], "negative")
        self.assertEqual(one("It doesn't work")["functionality"], "negative")
        self.assertEqual(one("not soft at all")["softness"], "negative")
        self.assertNotIn("dryness", one("No dryness at all, no drying"))
        self.assertEqual(one("It works well")["functionality"], "positive")
        self.assertEqual(one("no defects, good packaging", None).get("packaging"), "positive")

    def test_an_unsupported_category_reads_the_general_aspects_and_never_fails(self):
        for category in ("pet", "toys", "baby", "other", "not-a-category", None):
            result = aspects.extract(reviews(["Matibay at sulit", "Sira agad", "Maganda ang design"]), category, None)
            self.assertEqual(result["profile"], "general")
            self.assertGreater(len(result["aspects"]), 0)

    def test_a_very_long_review_is_read_in_bounded_time_and_quotes_stay_short(self):
        long_text = ("Ang lambot ng buhok ko pagkatapos gamitin, sobrang bango. " * 400) + "Hindi effective sa akin."
        self.assertGreater(len(long_text), 20000)
        started = time.perf_counter()
        result = aspects.extract(reviews([long_text, "Ang lambot ng buhok"]), "haircare", None)
        self.assertLess(time.perf_counter() - started, 3.0)
        softness = next(r for r in result["aspects"] if r["id"] == "softness")
        for quote in softness["positive"]["quotes"]:
            self.assertLessEqual(len(quote["text"]), EVIDENCE_POLICY["quote_chars"] + 1)
        self.assertEqual(softness["positive"]["reviews"], 2, "a long review still counts once")
        self.assertEqual(result["skipped_clauses"]["truncated_reviews"], 1, "the review was read only up to the limit, and that is counted")
        self.assertNotIn("functionality", {r["id"] for r in result["aspects"] if r["negative"]["reviews"]}, "text past the limit was not read")

    def test_reviews_never_expose_the_reviewer(self):
        comments = [{"comment_id": "1", "author": "J***s", "content": "Ang lambot ng buhok", "rating": 5}]
        result = aspects.extract(comments, "haircare", None)
        self.assertNotIn("J***s", json.dumps(result))
        self.assertNotIn("author", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
