"""Rules pc3: the labels behave, and are worded, by the kind of product."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))

import category_copy  # noqa: E402
from dashboard_utils import BADGE_COPY, _badge_copy, _conclusion, _labels, product_group  # noqa: E402
from defaketive_sentiment import product_category  # noqa: E402
from defaketive_sentiment.hazard_model import DEFECT, NOT_AS_DESCRIBED, SAFETY, LexiconHazardTagger  # noqa: E402


def tagger() -> LexiconHazardTagger:
    return LexiconHazardTagger(rules="0.4", counterfeit_rules="c2", sentiment_label=lambda text: "neutral")


def flagged(sentence: str, kind: str | None, label: str) -> bool:
    result = tagger().tag_sentence(sentence, product_kind=kind) if kind else tagger().tag_sentence(sentence)
    return label in (result.get("tags") or []) or label in (result.get("extra_tags") or [])


class HeatIsNotAlwaysAHazard(unittest.TestCase):
    """"init" is a heat hazard on a power bank and the weather, a comfort or the job of the product elsewhere."""

    CASES = (
        ("di ganu init", "haircare"),
        ("pantay ang init kapag nagluluto", "kitchen_dining"),
        ("init na init nako", "small_appliance"),
        ("ang init ng sapatos sa paa", "footwear"),
        ("amoy sunog ang kape", "food_beverage"),
        ("nakaka burn ng fat at calories", "sports_fitness"),
    )

    def test_the_same_words_are_a_hazard_on_a_power_bank(self) -> None:
        for sentence, _kind in self.CASES:
            with self.subTest(sentence=sentence):
                self.assertTrue(flagged(sentence, "powerbank", SAFETY), sentence)

    def test_and_are_not_a_hazard_on_the_product_they_describe(self) -> None:
        for sentence, kind in self.CASES:
            with self.subTest(sentence=sentence, kind=kind):
                self.assertFalse(flagged(sentence, kind, SAFETY), sentence)

    def test_a_real_burn_or_smoke_is_still_a_hazard_there(self) -> None:
        for sentence, kind in (
            ("umusok ang motor ng fan", "small_appliance"),
            ("nasunog ang balat ko, may paso", "haircare"),
            ("may usok at amoy sunog sa rice cooker", "kitchen_dining"),
            ("may uod at panis na", "food_beverage"),
        ):
            with self.subTest(sentence=sentence):
                self.assertTrue(flagged(sentence, kind, SAFETY), sentence)

    def test_a_category_with_no_file_is_read_as_before(self) -> None:
        for kind in (None, "other", "audio", "charger_cable", "home_decor_lighting"):
            with self.subTest(kind=kind):
                self.assertTrue(flagged("sobrang init", kind, SAFETY))


class WhatEachKindOfProductReports(unittest.TestCase):
    CASES = (
        ("nagka rashes ako pagkagamit", "skincare", SAFETY),
        ("allergic reaction ako sa lipstick", "makeup", SAFETY),
        ("may uod ang laman", "food_beverage", SAFETY),
        ("expired na po pagdating", "food_beverage", SAFETY),
        ("choking hazard for kids", "toys", SAFETY),
        ("bumagsak ang shelf namin", "furniture", SAFETY),
        ("amoy gas pagkabit ng regulator", "small_appliance", SAFETY),
        ("nawalan ng preno sa daan", "motorcycle", SAFETY),
        ("namatay ang aso pagkatapos", "pet", SAFETY),
        ("invalid code po", "digital_goods", DEFECT),
        ("mali ang reading ng thermometer", "medical_devices", DEFECT),
        ("hindi kasya ang size", "apparel", NOT_AS_DESCRIBED),
        ("iba ang flavor sa nakalagay", "food_beverage", NOT_AS_DESCRIBED),
    )

    def test_each_is_reported_on_its_own_kind_of_product(self) -> None:
        for sentence, kind, label in self.CASES:
            with self.subTest(sentence=sentence, kind=kind):
                self.assertTrue(flagged(sentence, kind, label), sentence)

    def test_none_of_them_changes_a_product_of_another_kind(self) -> None:
        # The same words on a phone, or with no category, are read as before.
        for sentence, _kind, label in self.CASES:
            with self.subTest(sentence=sentence):
                self.assertFalse(flagged(sentence, "phone", label), sentence)
                self.assertFalse(flagged(sentence, None, label), sentence)

    def test_a_denied_report_is_not_a_report(self) -> None:
        for sentence, kind in (
            ("walang rashes, okay sa balat", "skincare"),
            ("no allergic reaction at all", "makeup"),
            ("hindi expired, fresh pa", "food_beverage"),
        ):
            with self.subTest(sentence=sentence):
                self.assertFalse(flagged(sentence, kind, SAFETY), sentence)

    def test_an_added_safety_term_cannot_raise_an_alert_alone(self) -> None:
        # An unspecified safety concern is capped at severity 2 by the taxonomy.
        result = tagger().tag_sentence("nagka rashes ako pagkagamit", product_kind="skincare")
        self.assertEqual(result.get("hazard_subtype"), "safety_unspecified")


class FilesAreValid(unittest.TestCase):
    def test_every_file_loads_and_names_a_category_or_a_group(self) -> None:
        product_category.clear_cache()
        groups = {product_category.group_of(name) for name in product_category.CATEGORIES}
        for path in sorted(product_category.CATEGORY_DIR.glob("*.tsv")):
            stem = path.name[: -len(".add.tsv")] if path.name.endswith(".add.tsv") else path.stem
            with self.subTest(file=path.name):
                if stem.startswith("group_"):
                    self.assertIn(stem[len("group_"):], groups)
                else:
                    self.assertIn(stem, product_category.CATEGORIES)
        for name in product_category.CATEGORIES:
            product_category._exceptions(name)
            product_category._additions(name)


class WordsFollowTheProduct(unittest.TestCase):
    def test_every_group_has_every_line(self) -> None:
        groups = {product_category.group_of(name) for name in product_category.CATEGORIES} - {"other"}
        for group in groups:
            words = category_copy.profile(group)
            for category in BADGE_COPY:
                with self.subTest(group=group, category=category):
                    self.assertTrue(_badge_copy(category, words)["helper"])
                    self.assertTrue(_badge_copy(category, words)["none"])
            self.assertEqual(len(_labels(words)), len(BADGE_COPY))

    def test_a_lipstick_report_never_talks_about_chargers(self) -> None:
        electric = re.compile(r"battery|charger|charges|power bank|spark|smoke|shock|overheat", re.I)
        for group in ("beauty_health", "fashion", "food_grocery", "baby_kids_toys", "pets", "sports_outdoor", "office_media", "digital_services"):
            words = category_copy.profile(group)
            lines = [words["hazards"], *(text for item in words["badges"].values() for text in item.values())]
            for line in lines:
                with self.subTest(group=group, line=line):
                    self.assertIsNone(electric.search(line), line)

    def test_electronics_keeps_its_own_words(self) -> None:
        words = category_copy.profile("electronics")
        self.assertIn("Overheating", words["badges"]["safety"]["helper"])

    def test_group_is_read_from_the_title(self) -> None:
        self.assertEqual(product_group({"name": "Maybelline matte lipstick"}), "beauty_health")
        self.assertEqual(product_group({"name": "Xiaomi 20000mAh Power Bank"}), "electronics")
        self.assertEqual(product_group({"name": "x", "product_group": "pets"}), "pets")
        self.assertEqual(product_group({"name": "Mystery item"}), "other")

    def test_the_conclusion_names_what_matters_for_the_product(self) -> None:
        shares = {"sentiment_counts": {"positive": 50, "uncertain": 10, "negative": 40}, "positive_ratio_lower_bound": 0.4}
        badges = [{"category": "safety", "mentions": 3}, {"category": "defect", "mentions": 0}]
        food = _conclusion(shares, "safety_warning", badges, 100, category_copy.profile("food_grocery"))
        self.assertIn("spoiled", food["text"])
        self.assertNotIn("burning smell", food["text"])
        clean = {"sentiment_counts": {"positive": 90, "uncertain": 5, "negative": 5}, "positive_ratio_lower_bound": 0.85}
        fashion = _conclusion(clean, "no_warning_signs", [{"category": "safety", "mentions": 0}], 100, category_copy.profile("fashion"))
        self.assertEqual(fashion["assessment"], "Well reviewed")
        self.assertIn("red flags", fashion["assessment_note"])

    def test_no_name_says_caution_or_warning_signs(self) -> None:
        names = [*category_copy.ASSESSMENT.values(), category_copy.NO_RED_FLAGS, *category_copy.ASSESSMENT_NOTE.values()]
        for name in names:
            with self.subTest(name=name):
                self.assertNotRegex(name, r"(?i)caution|warning sign|hazard found")


if __name__ == "__main__":
    unittest.main()
