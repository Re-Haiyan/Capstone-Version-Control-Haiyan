"""Focused category-to-aspect tests; constructed examples are not real-data F1."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import aspect_profiles as profiles  # noqa: E402
import aspects  # noqa: E402


class CategoryProfileMappingTests(unittest.TestCase):
    def test_non_clothing_categories_do_not_inherit_clothing_fit(self) -> None:
        for category, group, expected in (
            ("bags", "fashion", "bags"),
            ("home_textile", "home_living", "home_textile"),
            ("health_supplements", "beauty_health", "supplements"),
        ):
            with self.subTest(category=category):
                self.assertEqual(profiles.profile_key(category, group), expected)
                labels = {aspect.label for aspect in profiles.aspects_for(category, group)}
                self.assertNotIn("fit and sizing", labels)

    def test_categories_do_not_inherit_unrelated_product_profiles(self) -> None:
        for category, group in (
            ("battery_solar", "electronics"),
            ("kitchen_dining", "home_living"),
            ("tv_display", "electronics"),
            ("automotive", "automotive_tools"),
            ("eyewear", "fashion"),
        ):
            with self.subTest(category=category):
                self.assertEqual(profiles.profile_key(category, group), "general")
        self.assertEqual(profiles.profile_key(None, "automotive_tools"), "general")
        self.assertEqual(profiles.profile_key(None, "fashion"), "general")
        self.assertEqual(profiles.profile_key("motorcycle", "automotive_tools"), "motorcycle")
        self.assertEqual(profiles.profile_key("charger_cable", "electronics"), "charger_cable")
        cable = {aspect.id for aspect in profiles.aspects_for("charger_cable", "electronics")}
        self.assertIn("charging", cable)
        self.assertIn("overheating", cable)
        self.assertNotIn("capacity", cable)
        self.assertEqual(profiles.profile_key("apparel", "fashion"), "apparel")

    def test_supplements_do_not_inherit_snack_spoilage_or_build_durability(self) -> None:
        items = profiles.aspects_for("health_supplements", "beauty_health")
        ids = {aspect.id for aspect in items}
        self.assertIn("expiry", ids)
        self.assertIn("taste", ids)
        self.assertNotIn("freshness", ids)
        self.assertNotIn("durability", ids)
        self.assertEqual(next(a.label for a in items if a.id == "build"), "overall quality")

    def test_bags_have_scoped_storage_and_zipper_aspects(self) -> None:
        sample = [
            {"comment_id": "bag-1", "content": "Maraming bulsa ang bag, very spacious", "rating": 5},
            {"comment_id": "bag-2", "content": "Sira ang zipper ng bag", "rating": 1},
        ]
        found = aspects.extract(sample, "bags", "fashion")
        by_id = {item["id"]: item for item in found["aspects"]}
        self.assertGreater(by_id["storage"]["positive"]["reviews"], 0)
        self.assertGreater(by_id["zipper"]["negative"]["reviews"], 0)

    def test_home_textile_retains_fabric_without_clothing_fit(self) -> None:
        found = profiles.aspects_for("home_textile", "home_living")
        self.assertIn("fabric", {a.id for a in found})
        self.assertNotIn("fit and sizing", {a.label for a in found})


if __name__ == "__main__":
    unittest.main()
