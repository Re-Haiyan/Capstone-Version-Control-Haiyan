"""Regression: the saved-detail route must supply source-backed review themes.

The frontend fetches /api/saved/detail BEFORE /api/products/detail; an
omitted aspects=True on that first endpoint silently hid all positive chips.
This uses fabricated review text and an in-memory catalog, never the live DB.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from server_under_test import app, server  # noqa: E402

SYNTHETIC = {
    "link": "https://www.lazada.com.ph/products/fictional-shampoo-i99999999.html",
    "name": "Silka Shampoo",
    "product_category": "haircare",
    "product_group": "beauty_health",
    "comments": [
        {"comment_id": "t1", "content": "Ang lambot ng buhok ko pagkatapos gamitin", "rating": 5},
        {"comment_id": "t2", "content": "My hair feels smoother after washing", "rating": 5},
        {"comment_id": "t3", "content": "Sobrang bango at lambot", "rating": 5},
        {"comment_id": "t4", "content": "Ang ganda ng amoy", "rating": 5},
        {"comment_id": "t5", "content": "Mabango and soft talaga", "rating": 5},
    ],
    "sentiment_summary": {
        "schema_version": "defaketive-summary-2",
        "usable_review_count": 5,
        "sentiment_counts": {"positive": 5, "uncertain": 0, "negative": 0},
        "positive_ratio_lower_bound": 0.70,
        "verdict": {"state": "no_warning_signs", "detail": "No warning-level flags."},
        "flags": {},
        "reports": {},
        "safety": {},
    }
}


class SavedDetailEvidenceTests(unittest.TestCase):
    def test_saved_details_contain_real_positive_themes_not_only_summary(self):
        product = copy.deepcopy(SYNTHETIC)
        original = copy.deepcopy(product)
        with (
            mock.patch.object(server, "_catalog", return_value=[product]),
            mock.patch.object(server, "rank_recommendations", return_value=[]),
            mock.patch.object(server, "_checked_with_current", return_value=True),
        ):
            response = app.test_client().get("/api/saved/detail", query_string={"link": product["link"]})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:350])
        report = response.get_json()["product"]
        conclusion = report["badge_view"]["conclusion"]
        self.assertIsNotNone(conclusion)
        evidence = conclusion.get("evidence")
        self.assertIsNotNone(evidence, "Saved-detail route must request aspects=True")
        self.assertGreater(evidence["reviews_considered"], 0)
        positives = [
            row for row in evidence["why"]
            if row["kind"] == "product" and row["polarity"] == "positive"
        ]
        self.assertTrue(positives, "Known synthetic hair compliments must yield an evidence-backed positive theme")
        self.assertTrue(any(row["quotes"] for row in positives))
        self.assertEqual(product, original, "Read-only saved detail must not mutate stored catalog objects")

    def test_saved_product_list_remains_lightweight(self):
        product = copy.deepcopy(SYNTHETIC)
        with mock.patch.object(server, "_catalog", return_value=[product]):
            response = app.test_client().get("/api/saved/products")
        self.assertEqual(response.status_code, 200)
        row = response.get_json()["products"][0]
        self.assertNotIn("comments", row)
        self.assertIsNone(row["badge_view"]["conclusion"].get("evidence"),
                          "List endpoints must not run expensive aspect extraction")


if __name__ == "__main__":
    unittest.main()
