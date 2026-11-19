"""Real-checkpoint category matrix and evidence retention through shopper APIs."""
from __future__ import annotations

import copy
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend/sentiment-analysis"), str(ROOT / "tests")]
from defaketive_sentiment import category_context, registry
from defaketive_sentiment.product_category import CATEGORIES, OTHER, classify_listing, normalize_category
from test_product_category import TITLES, PC3_TITLES
import dashboard_utils as du
import data_store


def product(title="Power Bank 20000mAh", texts=(), category=None, platform="lazada"):
    hosts = {"lazada": "www.lazada.com.ph/products/acceptance.html", "shopee": "shopee.ph/acceptance-i.123.456", "temu": "www.temu.com/goods.html?goods_id=601100000000001"}
    result = {"name": title, "link": "https://" + hosts[platform], "platform": platform,
              "comments": [{"content": text, "rating": 5} for text in texts]}
    if category is not None:
        result["category"] = category
    return result


class RealCheckpointMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = registry.load_model()

    def test_every_supported_category_with_real_shared_model(self):
        examples = {category: title for title, category in {**TITLES, **PC3_TITLES}.items()}
        self.assertTrue(set(CATEGORIES) - {OTHER} <= examples.keys())
        for category, profile in category_context._profiles()["profiles"].items():
            with self.subTest(category=category):
                self.assertIs(self.model, registry.load_model())
                title = examples[category]
                for polarity in ("positive", "negative"):
                    review = profile[polarity + "_phrases"][0]
                    analysis = self.model.analyze(review, 5, listing={"name": title})
                    context = analysis["sentiment"]["category_context"]
                    self.assertEqual(context["product_category"], category)
                    self.assertEqual(context["initial_label"], analysis["sentiment"]["initial_label"])
                    self.assertFalse(context["sentiment_overridden"])
                    self.assertIn(analysis["label"], {"positive", "neutral", "negative"})
                    self.assertIn("review_evidence", analysis)

    def test_saved_category_aliases_blank_unknown_and_title_precedence(self):
        for category in CATEGORIES:
            for alias in (category, category.upper(), category.replace("_", "-"), category.replace("_", " ")):
                with self.subTest(alias=alias):
                    self.assertEqual(normalize_category(alias), category)
                    result = du.analyze_products([product("XYZ", ["Works as expected."], alias)])[0]
                    self.assertEqual(result["product_category"], category)
        for category in ("", None, "unknown-department"):
            result = du.analyze_products([product("XYZ", ["Works as expected."], category)])[0]
            self.assertEqual(result["product_category"], OTHER)
            self.assertEqual(result["comments"][0]["sentiment_analysis"]["sentiment"]["category_context"]["status"], "unclassified")
        self.assertEqual(classify_listing({"name": "Solar battery", "product_category": "gaming"}), "battery_solar")

    def test_hazards_on_positive_reviews_and_negation_pairs(self):
        for text in (
            "Excellent charger, great quality, fast charging, very happy and highly recommended! The cable sparked once.",
            "Love this charger! Fast charging, beautiful design, excellent quality and great value. It burned my hand once.",
            "Maganda at sulit, mabilis mag charge, satisfied ako! Pero umusok ang charger.",
        ):
            with self.subTest(real_positive=text):
                result = self.model.analyze(text, 5, listing={"name": "Phone Charger"})
                self.assertEqual(result["sentiment"]["initial_label"], "positive")
                self.assertIn("safety", result["review_tags"])
                self.assertTrue(result["review_evidence"]["safety"]["spans"])
        for affirmative, denied in (
            ("The charger overheated and smoked.", "The charger did not overheat or smoke."),
            ("Umusok ang charger at amoy sunog.", "Walang usok o amoy sunog ang charger."),
            ("Great charger, but it sparked and burned my hand.", "Great charger, no sparks and no burns."),
        ):
            with self.subTest(affirmative=affirmative):
                yes = self.model.analyze(affirmative, 5, listing={"name": "Phone Charger"})
                no = self.model.analyze(denied, 5, listing={"name": "Phone Charger"})
                self.assertIn("safety", yes["review_tags"])
                self.assertNotIn("safety", no["review_tags"])
                self.assertTrue(yes["review_evidence"]["safety"]["spans"])
        # Force the sentiment path Positive to prove it cannot gate hazard checks.
        with mock.patch.object(self.model.sentiment, "analyze", return_value={"label": "positive", "classifier": {"probabilities": {"positive": 1.0}}}):
            result = self.model.analyze("Great charger, but it sparked and burned my hand.", 5, listing={"name": "Phone Charger"})
        self.assertEqual(result["label"], "positive")
        self.assertIn("safety", result["review_tags"])

    def test_magaan_is_portability_praise_or_a_flimsy_stand_complaint(self):
        cases = (("Power Bank", "Magaan at madaling dalhin.", "positive"),
                 ("Phone Stand", "Magaan pero marupok ang stand.", "negative"))
        for title, text, expected in cases:
            with self.subTest(title=title):
                result = self.model.analyze(text, 5, listing={"name": title})
                context = result["sentiment"]["category_context"]
                self.assertEqual(context["context_signal"], expected)
                self.assertTrue(context["matched_profile_phrase"])
                self.assertFalse(context["sentiment_overridden"])

    def test_empty_few_missing_and_saved_exports_keep_evidence(self):
        for texts in ([], ["Great charger, but it sparked and burned my hand."]):
            for platform in ("lazada", "shopee", "temu"):
                with self.subTest(count=len(texts), platform=platform):
                    original = product("Phone Charger", texts, platform=platform)
                    analyzed = du.analyze_products([original])[0]
                    view = du.badge_view(analyzed)
                    self.assertEqual(view["reviews_analyzed"], len(texts))
                    if not texts:
                        self.assertEqual(view["state"], "insufficient_evidence")
                    else:
                        self.assertGreater(view["counts"]["safety"], 0)
                        with tempfile.TemporaryDirectory() as folder:
                            database = Path(folder) / "isolated.db"
                            data_store.save_products([analyzed], path=database)
                            restored = data_store.load_saved_products(database)[0]
                        self.assertEqual(restored["comments"], analyzed["comments"])
                        exported = list(csv.DictReader(io.StringIO(du.csv_bytes(du.review_rows([restored])).decode("utf-8-sig"))))[0]
                        self.assertEqual(exported["Review"], texts[0])
                        self.assertIn("safety", exported["Review-reported concerns"])
                        self.assertTrue(json.loads(exported["Concern evidence"])["safety"]["spans"])
                        self.assertIn(exported["Initial sentiment"], {"positive", "neutral", "negative"})
        self.assertEqual(du.badge_view(du.analyze_products([{"name": "Phone Charger", "link": "fixture"}])[0])["state"], "insufficient_evidence")

    def test_runtime_failure_never_returns_valid_report(self):
        source = product(texts=["Works great."])
        before = copy.deepcopy(source)
        with mock.patch.object(self.model, "analyze_batch", side_effect=RuntimeError("acceptance inference failure")):
            with self.assertRaisesRegex(registry.ModelUnavailableError, "inference failed"):
                du.analyze_products([source])
        self.assertEqual(source, before)
        with mock.patch.object(self.model, "analyze_batch", return_value=[]):
            with self.assertRaisesRegex(registry.ModelUnavailableError, "incomplete results"):
                du.analyze_products([source])

    def test_invalid_logits_and_label_mapping_fail_closed(self):
        from defaketive_sentiment.transformer_sentiment import TransformerModelError, read_manifest
        classifier = self.model.sentiment.trained_classifier
        for logits in (np.array([[float("nan"), 0, 0]]), np.array([[0, 1]])):
            with mock.patch.object(classifier.session, "run", return_value=[logits]):
                with self.assertRaises(TransformerModelError):
                    classifier.predict("Works great.")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            manifest = copy.deepcopy(classifier.manifest)
            manifest["labels"] = ["positive", "neutral", "negative"]
            (path / "manifest.json").write_text(json.dumps(manifest))
            for name in manifest["files"]:
                # Hash verification is tested by the loader; isolate the label-order check here.
                (path / name).touch()
            with mock.patch("defaketive_sentiment.transformer_sentiment.file_sha256", side_effect=lambda p: manifest["files"][p.name]):
                with self.assertRaisesRegex(TransformerModelError, "label order"):
                    read_manifest(path)


class ShopperRoutes(unittest.TestCase):
    def test_keyword_product_and_category_commands(self):
        from server_under_test import webapp
        cases = (("power bank", None), ("https://www.lazada.com.ph/products/example-i123456.html", "--product-url"),
                 ("https://www.lazada.com.ph/shop-mobiles/", "--category-url"),
                 ("https://www.lazada.com.ph/catalog/?q=charger", "--category-url"))
        for query, option in cases:
            with self.subTest(query=query):
                command, _ = webapp._command_for_scrape(query, "lazada", 1, 1)
                self.assertEqual(command[-1], query)
                if option:
                    self.assertEqual(command[-2], option)
                else:
                    self.assertNotIn("--product-url", command)
                    self.assertNotIn("--category-url", command)

    def test_shopper_saved_grid_selection_and_conclusion_for_each_marketplace(self):
        from server_under_test import app
        import server
        from saved_pool import SavedPool
        for platform in ("lazada", "shopee", "temu"):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as folder:
                analyzed = du.analyze_products([product(texts=["Maganda at sulit!"], platform=platform)])
                database = Path(folder) / "products.db"
                data_store.save_products(analyzed, path=database)
                with mock.patch.object(server, "pool", SavedPool(database)):
                    client = app.test_client()
                    grid = client.get("/api/saved/products").get_json()["products"]
                    self.assertEqual(len(grid), 1)
                    detail = client.get("/api/saved/detail", query_string={"link": grid[0]["link"]})
                    self.assertEqual(detail.status_code, 200)
                    report = detail.get_json()["product"]
                    self.assertTrue(report["badge_view"]["available"])
                    self.assertEqual(report["comments"][0]["content"], "Maganda at sulit!")
                    self.assertIn("category_context", report["comments"][0]["sentiment_analysis"]["sentiment"])
                    for query in ("Power Bank", grid[0]["link"]):
                        response = client.post("/api/search", json={"query": query, "platform": platform, "live": False})
                        self.assertEqual(response.status_code, 200)

    def test_unsupported_live_routes_are_explicit(self):
        from server_under_test import app
        client = app.test_client()
        for platform in ("shopee", "temu"):
            for query in ("power bank", product(platform=platform)["link"]):
                with self.subTest(platform=platform, query=query):
                    response = client.post("/api/search", json={"query": query, "platform": platform, "live": True})
                    self.assertEqual(response.status_code, 400)
                    self.assertTrue(response.get_json().get("error"))


if __name__ == "__main__":
    unittest.main()
