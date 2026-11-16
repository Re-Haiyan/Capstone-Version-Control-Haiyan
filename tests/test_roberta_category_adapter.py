"""Category-aware XLM-R adapter is research-only and cannot rewrite decisions."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "sentiment-analysis"))

from defaketive_sentiment import category_adapter as a  # noqa: E402


class CategoryFeatures(unittest.TestCase):
    def test_fails_closed_when_category_is_wrong_or_not_recognized(self):
        self.assertEqual(a.title_category("PowMr Hybrid Solar Inverter MPPT Solar Controller"), ("other", "other"))
        self.assertEqual(a.title_category("Unknown Generic Marketplace Product 991"), ("other", "other"))
        self.assertEqual(a.title_category("Samsung Galaxy A15 Smartphone")[0], "phone")
        self.assertEqual(a.title_category("Cotton T-shirt Oversized")[0], "apparel")

    def test_category_and_ambiguous_cue_are_used_as_features_not_new_encoder_text(self):
        phone = a.context_features("Maganda pero manipis", "Samsung Galaxy A15 Smartphone")
        shirt = a.context_features("Maganda pero manipis", "Cotton T-shirt Oversized")
        self.assertIn("group=electronics:cue=thin", phone)
        self.assertIn("group=fashion:cue=thin", shirt)
        self.assertNotEqual(phone, shirt)
        self.assertEqual(a.context_features("sobrang nipis", "Random Generic Item"), {})

    def test_sparse_training_features_are_compatible_with_one_item_inference(self):
        texts = ["Ang manipis at ang ganda", "Sobrang nipis ng tela", "Sobrang init"]
        titles = ["Samsung Galaxy Smartphone", "Cotton T-shirt", "Solar Inverter MPPT"]
        p = np.array([[0.1, 0.1, 0.8], [0.7, 0.2, 0.1], [0.6, 0.3, 0.1]])
        vw = TfidfVectorizer().fit(texts)
        vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)).fit(texts)
        cv = DictVectorizer(sparse=True).fit([a.context_features(t, x) for t, x in zip(texts, titles)])
        x = a.model_features(texts, [5, 1, 1], p, titles, vw, vc, cv)
        single = a.model_features([texts[0]], [5], p[:1], titles[:1], vw, vc, cv)
        self.assertEqual(single.shape[1], x.shape[1])
        self.assertTrue(np.allclose(single.toarray()[0], x.toarray()[0]))
        with self.assertRaises(ValueError):
            a.model_features(["hi"], [5], np.array([[0.3, 0.3]]), ["phone"], vw, vc, cv)

    def test_shadow_is_default_off_and_requires_original_encoder_sha(self):
        with mock.patch.dict(os.environ, {a.SHADOW_ENV: "", a.ENV: "missing.joblib"}):
            self.assertIsNone(a.shadow("thin", 5, {"negative": 0, "neutral": 0, "positive": 1},
                                        {"name": "Samsung Galaxy Smartphone"}, "positive", "abc"))
        with mock.patch.dict(os.environ, {a.SHADOW_ENV: "shadow", a.ENV: ""}):
            self.assertIsNone(a.shadow("thin", 5, {"negative": 0, "neutral": 0, "positive": 1},
                                        {"name": "Samsung Galaxy Smartphone"}, "positive", "abc"))
        with mock.patch.dict(os.environ, {a.SHADOW_ENV: "shadow", a.ENV: "missing.joblib"}):
            self.assertIsNone(a.shadow("thin", 5, {"negative": 0, "neutral": 0, "positive": 1},
                                        {"name": "Samsung Galaxy Smartphone"}, "positive", None))

    def test_artifact_is_rejected_if_different_encoder_category_rules_or_fake_qualification(self):
        with tempfile.TemporaryDirectory() as t:
            artifact = Path(t) / "adapter.joblib"
            artifact.write_bytes(b"NOT_A_MODEL")
            source = Path(a.__file__).with_name("product_category.py")
            correct = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest = {
                "stage": "research_shadow",
                "qualified_for_integration": False,
                "revision": a.REVISION,
                "base_encoder_sha256": "original-encoder",
                "source_code_sha256": correct,
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
            target = artifact.with_suffix(".json")
            target.write_text(json.dumps(manifest))
            self.assertEqual(a.validate_manifest(artifact, "original-encoder"), manifest)
            for patch in (
                {"base_encoder_sha256": "wrong"},
                {"source_code_sha256": "wrong"},
                {"qualified_for_integration": True},
                {"artifact_sha256": "wrong"},
            ):
                changes = {**manifest, **patch}
                target.write_text(json.dumps(changes))
                with self.subTest(patch=patch), self.assertRaises(ValueError):
                    a.validate_manifest(artifact, "original-encoder")


if __name__ == "__main__":
    unittest.main()
