"""Synthetic-only integrity tests; no synthetic rows enter real Phase 4 data."""
from __future__ import annotations

import csv
import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent /
    "research/product_specific_conclusions/phase4/intake.py"
)
spec = importlib.util.spec_from_file_location("phase4_intake", SCRIPT)
mod = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def raw(
    listing_id: str = "new-unique-item-123",
    review_text: str = "My ceramic kettle worked well and boiled water quickly on my first day.",
    **overrides,
) -> dict:
    entry = {
        "marketplace": "lazada",
        "listing_id": listing_id,
        "listing_url": f"https://www.lazada.com.ph/products/{listing_id}.html",
        "listing_title": f"Newly listed synthetic ceramic kettle model {listing_id}",
        "category": "small_appliance",
        "group": "home_living",
        "language": "taglish",
        "review_text": review_text,
        "stars": 4,
        "collection_date": "2026-11-14",
        "source_kind": "authorized_export",
        "source_id": "synthetic-test-batch-001",
        "rights_confirmed": "yes",
    }
    entry.update(overrides)
    return entry


def entry(item: dict) -> mod.Entry:
    return mod.parse_entry(item, 1)


def distinct_review(listing_id: str, number: int = 1) -> str:
    """Differ in several actual tokens, not just a product number.

    Otherwise a correctly strict >=0.80 Jaccard filter would remove
    different synthetic examples and make the test incorrectly expect 50.
    """
    code = listing_id.replace("-", "") + str(number)
    return (
        "Synthetic product experience with specific usage and observed quality: "
        f"applause{code} roughness{code} compactness{code} durability{code} "
        f"comfort{code} alignment{code} "
        "after daily use in a comparison with an older item"
    )


def fake_history(texts=(), titles=(), hashes=()):
    index = mod.OverlapIndex()
    for text in texts:
        index.add(text)
    return index, set(titles), set(hashes)


class InputContract(unittest.TestCase):
    def test_requires_explicit_rights_and_rejects_personal_fields(self):
        baseline = raw()
        for wrong in (
            {**baseline, "rights_confirmed": "no"},
            {**baseline, "reviewer_id": "no-private-reviewer-id"},
            {**baseline, "buyer_name": "not-allowed"},
            {**baseline, "source_kind": "unknown-source"},
            {**baseline, "collection_date": "2999-01-01"},
            {**baseline, "stars": True},
        ):
            with self.subTest(wrong=wrong):
                with self.assertRaises(mod.IntakeError):
                    entry(wrong)

    def test_rejects_possible_private_data_in_text_or_title(self):
        for value in (
            "The charger is good contact me at 09171234567 please",
            "I like this product contact me at alice@example.com",
            "I received my order and this is OTP 123456 please use it",
            "The item works fine, see my other review at https://example.com",
        ):
            with self.subTest(value=value):
                with self.assertRaises(mod.IntakeError):
                    entry(raw(review_text=value))
        with self.assertRaises(mod.IntakeError):
            entry(raw(listing_title="Shop me: alice@example.com - awesome ceramic kettle"))

    def test_rejects_invalid_url_and_empty_or_short_review(self):
        for row in (
            raw(listing_url="http://site.example/item"),
            raw(listing_url="https://user:password@example.com/item"),
            raw(review_text="Great."),
            raw(group=""),
        ):
            with self.subTest(row=row):
                with self.assertRaises(mod.IntakeError):
                    entry(row)

    def test_marketplace_domain_and_listing_path_must_be_realistic(self):
        with self.assertRaises(mod.IntakeError):
            entry(raw(listing_url="https://fake-lazada.example.com/p/item"))
        with self.assertRaises(mod.IntakeError):
            entry(raw(listing_url="https://www.lazada.com.ph/"))
        self.assertEqual(entry(raw()) .marketplace, "lazada")

    def test_refuses_malformed_jsonl_and_duplicate_unexpected_field(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "bad.jsonl"
            bad.write_text(json.dumps({**raw(), "user": "hidden"}), encoding="utf-8")
            with self.assertRaises(mod.IntakeError):
                mod.read_input(bad)
            bad.write_text('{"review_text": "broken json"\n', encoding="utf-8")
            with self.assertRaises(mod.IntakeError):
                mod.read_input(bad)


class SplitAndOverlap(unittest.TestCase):
    def test_same_product_goes_to_exactly_one_split(self):
        keys = [f"synthetic-item-{i:03d}" for i in range(60)]
        assignments = {mod.split_for("lazada", key) for key in keys}
        self.assertEqual(assignments, {"D3", "V3", "F2"})
        chosen = keys[8]
        self.assertEqual(
            mod.split_for("lazada", chosen),
            mod.split_for("LAZADA", chosen),
        )
        self.assertEqual(mod.product_hash("lazada", chosen),
                         mod.product_hash("LAZADA", chosen))

    def test_overlap_index_rejects_exact_punctuation_and_near_duplicates(self):
        index = mod.OverlapIndex()
        text = "Very light and comfortable to wear on my short daily commute to work"
        index.add(text)
        self.assertTrue(index.is_duplicate(text.upper()))
        self.assertTrue(index.is_duplicate(text + "!"))
        self.assertTrue(index.is_duplicate(
            "Very light and comfortable to wear on my daily commute to work"
        ))
        self.assertFalse(index.is_duplicate(
            "This large item arrived yesterday and the package was extremely damaged"
        ))

    def test_historical_link_and_title_block_reused_products(self):
        first = raw()
        second = raw(listing_id="different-item")
        hist = fake_history(
            titles={mod.norm(first["listing_title"])},
            hashes={mod.historic_link_hash(second["listing_url"])},
        )
        result = mod.build([entry(first), entry(second)], hist)
        self.assertEqual(result["manifest"]["rows_accepted"], 0)
        self.assertEqual(result["manifest"]["rows_rejected_by_reason"]["historical_product_overlap"], 2)

    def test_historical_review_text_and_near_duplicates_are_excluded(self):
        historic = "Really fast cooking results with the rice cooker and nice build quality."
        original = raw(review_text=historic)
        repeated = raw(
            listing_id="new-item-two",
            review_text="Really fast cooking results with the rice cooker and nice build quality!",
        )
        result = mod.build(
            [entry(original), entry(repeated)],
            fake_history(texts=[historic])
        )
        self.assertEqual(result["manifest"]["rows_accepted"], 0)
        self.assertEqual(result["manifest"]["rows_rejected_by_reason"]["historical_or_internal_duplicate"], 2)

    def test_reused_public_listing_url_cannot_get_different_product_ids(self):
        first = entry(raw(listing_id="initial-product-key"))
        second = entry(raw(
            listing_id="renamed-product-key",
            listing_url=first.listing_url,
            review_text=distinct_review("changed"),
        ))
        with self.assertRaises(mod.IntakeError):
            mod.build([first, second], fake_history())

    def test_one_product_id_cannot_point_to_different_listing_urls(self):
        first = entry(raw(listing_id="first-key"))
        second = entry(raw(
            listing_id="first-key",
            listing_url="https://www.lazada.com.ph/products/different-key.html",
            review_text=distinct_review("different-url"),
        ))
        with self.assertRaises(mod.IntakeError):
            mod.build([first, second], fake_history())

    def test_multiple_reviews_cannot_leak_product_across_splits(self):
        keys = [f"sample-unique-item-{i}" for i in range(25)]
        inputs = []
        for key in keys:
            for index in (1, 2):
                inputs.append(entry(raw(
                    listing_id=key,
                    review_text=distinct_review(key, index),
                )))
        result = mod.build(inputs, fake_history())
        product_places = {}
        for split, rows in result["rows"].items():
            for r in rows:
                product_places.setdefault(r["product_hash"], set()).add(split)
        self.assertTrue(all(len(places) == 1 for places in product_places.values()))
        self.assertEqual(sum(result["manifest"]["counts"].values()), 50)
        self.assertFalse(result["manifest"]["research_ready"])

    def test_build_is_order_invariant(self):
        inputs = [
            entry(raw(
                listing_id=f"new-synthetic-{i}",
                review_text=distinct_review(f"new-synthetic-{i}"),
            ))
            for i in range(30)
        ]
        front = mod.build(inputs, fake_history())
        back = mod.build(list(reversed(inputs)), fake_history())
        self.assertEqual(front, back)

    def test_phase3_stored_hashes_and_full_locked_pack_are_loaded(self):
        index, titles, hashes = mod.historical_index()
        self.assertGreater(len(index.docs), 100)
        self.assertGreaterEqual(len(titles), 35)
        self.assertGreater(len(hashes), 20)
        self.assertTrue(index.is_duplicate(
            "fast and efficient cook guaranteed and safe to use walang usok o overheat "
            "made of plastic material Pero sa loob metal Sana magtagal naman🙏🙏🙏"
        ))


class SealedOutputs(unittest.TestCase):
    def test_no_f2_text_in_dev_folder_and_private_files(self):
        keys = [f"synthetic-key-{i:03d}" for i in range(65)]
        inputs = [
            entry(raw(
                listing_id=key,
                review_text=distinct_review(key),
            )) for key in keys
        ]
        out = mod.build(inputs, fake_history())
        self.assertGreater(len(out["rows"]["F2"]), 0)
        with tempfile.TemporaryDirectory() as root:
            dev = Path(root) / "development"
            vault = Path(root) / "separate-final-vault"
            mod.emit(out, dev, vault)
            manifest = json.loads((dev / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["f2_vault_file_count"], len(out["rows"]["F2"]))
            self.assertEqual(
                {p.name for p in dev.iterdir()},
                {"D3.csv", "V3.csv", "manifest.json"},
            )
            self.assertEqual(
                {p.name for p in vault.iterdir()},
                {"F2_SEALED_DO_NOT_OPEN.csv"},
            )
            self.assertNotIn(out["rows"]["F2"][0]["review_text"],
                             (dev / "manifest.json").read_text(encoding="utf-8"))
            if __import__("os").name == "posix":
                for path in (*dev.iterdir(), *vault.iterdir()):
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(mod.IntakeError):
                mod.emit(out, dev, vault)

    def test_refuse_any_development_output_inside_repository(self):
        self.assertFalse(mod._outside_repo(mod.ROOT / "phase4_private"))
        with tempfile.TemporaryDirectory() as temp:
            self.assertTrue(mod._outside_repo(Path(temp) / "new-work"))


if __name__ == "__main__":
    unittest.main()
