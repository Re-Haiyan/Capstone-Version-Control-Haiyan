"""Synthetic, standard-library-only tests for the honest Hazard Checker 0.80 gate."""

from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("hazard_80_gate", ROOT / "research/hazard_80_gate.py")
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def save(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class HazardEightyGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.reference = root / "fresh.csv"
        self.predictions = root / "predictions.csv"
        self.old = root / "old.csv"
        save(self.old, ["product_id", "review_text"],
             [{"product_id": "history-1", "review_text": "Previously checked"}])
        self.reference_rows = [
            {"review_id": str(i), "product_id": "fresh-" + str(i),
             "review_text": "Synthetic distinct product review " + str(i),
             "true_flags": flag, "annotation_method": "ai_assisted",
             "adjudicated": "false", "rights_confirmed": "true"}
            for i, flag in enumerate(gate.FLAGS)
        ]
        self.prediction_rows = [
            {"review_id": str(i), "predicted_flags": flag}
            for i, flag in enumerate(gate.FLAGS)
        ]
        self.write()

    def write(self) -> None:
        save(self.reference,
             ["review_id", "product_id", "review_text", "true_flags",
              "annotation_method", "adjudicated", "rights_confirmed"],
             self.reference_rows)
        save(self.predictions, ["review_id", "predicted_flags"], self.prediction_rows)

    def test_ai_only_perfect_agreement_is_not_independent_accuracy(self) -> None:
        report = gate.score(self.reference, self.predictions, [self.old], min_positives=1)
        self.assertEqual(report["macro_f1"], 1.0)
        self.assertEqual(report["exact_match_accuracy"], 1.0)
        self.assertTrue(report["target_met_on_reference"])
        self.assertFalse(report["independently_verified_target_met"])
        self.assertFalse(report["production_release_approved"])

    def test_support_is_not_inferred_from_perfect_scores(self) -> None:
        report = gate.score(self.reference, self.predictions, [self.old])
        self.assertFalse(report["sufficient_support"])
        self.assertFalse(report["target_met_on_reference"])

    def test_false_positives_and_false_negatives_count(self) -> None:
        self.prediction_rows[0]["predicted_flags"] = "safety"
        self.write()
        report = gate.score(self.reference, self.predictions, [self.old], min_positives=1)
        self.assertEqual(report["per_class"]["defect"]["fn"], 1)
        self.assertEqual(report["per_class"]["safety"]["fp"], 1)
        self.assertFalse(report["target_met_on_reference"])

    def test_rejects_old_product_or_duplicate_review_text(self) -> None:
        self.reference_rows[0]["product_id"] = "history-1"
        self.write()
        with self.assertRaisesRegex(gate.GateError, "overlap"):
            gate.score(self.reference, self.predictions, [self.old], min_positives=1)
        self.reference_rows[0]["product_id"] = "fresh-0"
        self.reference_rows[0]["review_text"] = "Previously checked"
        self.write()
        with self.assertRaisesRegex(gate.GateError, "overlap"):
            gate.score(self.reference, self.predictions, [self.old], min_positives=1)

    def test_rejects_uncleared_rights_and_bad_ids(self) -> None:
        self.reference_rows[0]["rights_confirmed"] = "false"
        self.write()
        with self.assertRaisesRegex(gate.GateError, "rights"):
            gate.score(self.reference, self.predictions, [self.old], min_positives=1)
        self.reference_rows[0]["rights_confirmed"] = "true"
        self.prediction_rows.pop()
        self.write()
        with self.assertRaisesRegex(gate.GateError, "IDs mismatch"):
            gate.score(self.reference, self.predictions, [self.old], min_positives=1)

    def test_rejects_unrecognised_flags_and_missing_exclusions(self) -> None:
        self.prediction_rows[0]["predicted_flags"] = "unsafe"
        self.write()
        with self.assertRaisesRegex(gate.GateError, "unknown flags"):
            gate.score(self.reference, self.predictions, [self.old], min_positives=1)
        with self.assertRaisesRegex(gate.GateError, "exclude"):
            gate.score(self.reference, self.predictions, [], min_positives=1)

    def test_human_reference_is_only_a_declared_method(self) -> None:
        for row in self.reference_rows:
            row["annotation_method"] = "human_adjudicated"
            row["adjudicated"] = "true"
        self.write()
        report = gate.score(self.reference, self.predictions, [self.old], min_positives=1)
        self.assertTrue(report["annotation_claims_human_adjudication"])
        self.assertFalse(report["independent_provenance_verified"])
        self.assertTrue(report["target_met_on_reference"])
        self.assertFalse(report["independently_verified_target_met"])
        self.assertFalse(report["production_release_approved"])


if __name__ == "__main__":
    unittest.main()
