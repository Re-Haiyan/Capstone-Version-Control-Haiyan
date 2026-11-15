"""The saved-report route the report page actually uses (/api/saved/detail) must carry the explanation when the feature is on.

Found on the live VM on 2026-11-15: the feature was switched on and no saved report showed an explanation, because only the older
session route (/api/products/detail) asked for it. The unit tests called badge_view directly and the browser test used recorded
payloads, so neither exercised this route.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from server_under_test import app  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "backend"))
import dashboard_utils  # noqa: E402


class SavedDetailCarriesTheExplanation(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        cards = self.client.get("/api/saved/products").get_json()["products"]
        self.links = [c["link"] for c in cards if (c.get("reviews_collected") or 0) >= 20][:6]
        self.assertTrue(self.links, "the development database has saved products with reviews")

    def conclusions(self):
        out = {}
        for link in self.links:
            response = self.client.get("/api/saved/detail", query_string={"link": link})
            self.assertEqual(response.status_code, 200)
            out[link] = response.get_json()["product"]["badge_view"]["conclusion"]
        return out

    def test_on_the_route_returns_evidence_and_off_it_does_not_with_the_same_decision(self):
        with mock.patch.object(dashboard_utils, "REASONS_ENABLED", True):
            on = self.conclusions()
        with mock.patch.object(dashboard_utils, "REASONS_ENABLED", False):
            off = self.conclusions()
        self.assertTrue(any("evidence" in c for c in on.values()), "explanations on: at least one saved report carries evidence")
        self.assertFalse(any("evidence" in c for c in off.values()), "explanations off: no saved report carries evidence")
        for link in self.links:
            self.assertEqual(on[link]["decision"], off[link]["decision"])
            self.assertEqual(on[link]["headline"], off[link]["headline"])


if __name__ == "__main__":
    unittest.main()
