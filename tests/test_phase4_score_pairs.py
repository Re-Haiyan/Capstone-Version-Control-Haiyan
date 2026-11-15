"""Synthetic-only Phase 4 pair scoring tests. No test row is real evidence."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "research/product_specific_conclusions/phase4/score_pairs.py"
SPEC = importlib.util.spec_from_file_location("score_pairs_phase4", SCRIPT)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def pair(aspect: str, polarity: str = "positive", kind: str = "product") -> dict:
    return {"kind": kind, "aspect_id": aspect, "polarity": polarity}


def record(rid: str, pairs: list[dict], status: str | None = None) -> dict:
    r = {"review_id": rid, "pairs": pairs}
    if status is not None:
        r["status"] = status
    return r


class TestPhase4Scorer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.reviews = self.folder / "V3.csv"
        self.reference = self.folder / "reference.jsonl"
        self.baseline = self.folder / "baseline.jsonl"
        self.candidate = self.folder / "candidate.jsonl"
        self.provenance = self.folder / "provenance.json"
        self.out = self.folder / "results.json"
        rows = [
            {"review_id": "abc" + str(i), "product_hash": "prod" + str(i // 2),
             "language": "taglish" if i % 2 else "en",
             "category": "electronics" if i % 2 else "apparel",
             "group": "test", "review_text": f"Entirely synthetic test {i} text, not a customer review."}
            for i in range(6)
        ]
        with self.reviews.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        self.ref_rows = [
            record("abc0", [pair("size")], "complete"),
            record("abc1", [pair("build_quality", "negative")], "complete"),
            record("abc2", [pair("delivery", kind="service")], "complete"),
            record("abc3", [], "complete"),
            record("abc4", [pair("authenticity", "negative", "trust")], "complete"),
            record("abc5", [pair("size", "negative")], "complete"),
        ]
        self.base_rows = [
            record("abc0", [pair("size")]),
            record("abc1", []),
            record("abc2", []),
            record("abc3", []),
            record("abc4", [pair("authenticity", "negative", "trust")]),
            record("abc5", []),
        ]
        self.candidate_rows = [
            record("abc0", [pair("size")]),
            record("abc1", [pair("build_quality", "negative")]),
            record("abc2", [pair("delivery", kind="service")]),
            record("abc3", []),
            record("abc4", [pair("authenticity", "negative", "trust")]),
            record("abc5", [pair("size", "negative")]),
        ]
        self.write_rows(self.reference, self.ref_rows)
        self.write_rows(self.baseline, self.base_rows)
        self.write_rows(self.candidate, self.candidate_rows)
        self.provenance.write_text(json.dumps({
            "reference_type": "ai_assisted",
            "annotator_model": "SYNTHETIC FIXTURE - NOT A REAL MODEL",
            "annotation_date": "2026-11-15",
            "rubric_sha256": "a" * 64,
            "accepted_csv_sha256": M.file_sha256(self.reviews),
            "blind_to_predictions": True,
        }), encoding="utf-8")

    @staticmethod
    def write_rows(path, data):
        path.write_text("\n".join(json.dumps(r) for r in data) + "\n", encoding="utf-8")

    def cli(self, split="V3", extra=()):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--split", split,
             "--reviews", str(self.reviews), "--reference", str(self.reference),
             "--baseline", str(self.baseline), "--candidate", str(self.candidate),
             "--provenance", str(self.provenance), "--out", str(self.out),
             *extra],
            capture_output=True, text=True, cwd=ROOT,
        )

    def test_precise_counts_and_no_raw_text_exposure(self):
        r = self.cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(out["review_count"], 6)
        self.assertEqual(out["task_metrics"]["candidate"]["T1"]["tp"], 3)
        self.assertEqual(out["task_metrics"]["baseline"]["T1"]["fn"], 2)
        self.assertEqual(out["task_metrics"]["candidate"]["T2"]["tp"], 1)
        self.assertEqual(out["task_metrics"]["candidate"]["T3"]["tp"], 1)
        self.assertEqual(out["task_metrics"]["candidate"]["T1"]["f1"], 1.0)
        self.assertTrue(out["t1_all_three_at_least_080_on_this_proxy"])
        self.assertFalse(out["adoption_or_production_approved"])
        self.assertIn("AI-assisted proxy", out["reference_method"])
        visible = self.out.read_text(encoding="utf-8") + r.stdout
        self.assertNotIn("Entirely synthetic test", visible)
        self.assertNotIn("abc0", visible)
        self.assertNotIn("prod0", visible)
        self.assertEqual(out["product_cluster_bootstrap_t1_f1_delta"]["clusters"], 3)
        self.assertIn("en", out["by_language"])
        self.assertIn("apparel", out["by_category"])

    def test_refuse_repeated_scoring_that_overwrites(self):
        self.assertEqual(self.cli().returncode, 0)
        self.assertNotEqual(self.cli().returncode, 0)

    def test_refuses_reference_missing_row_and_pending_labels(self):
        for changed in (self.ref_rows[:-1], [
            *self.ref_rows[:-1],
            record("abc5", [pair("size", "negative")], "pending")
        ]):
            self.write_rows(self.reference, changed)
            r = self.cli()
            self.assertEqual(r.returncode, 2)
            self.assertFalse(self.out.exists())

    def test_no_silent_simplification_of_ambiguous_rows(self):
        self.ref_rows[0]["status"] = "unclear"
        self.write_rows(self.reference, self.ref_rows)
        r = self.cli()
        self.assertEqual(r.returncode, 2)

    def test_rejects_mismatched_provenance(self):
        prov = json.loads(self.provenance.read_text())
        prov["accepted_csv_sha256"] = "0" * 64
        self.provenance.write_text(json.dumps(prov))
        self.assertEqual(self.cli().returncode, 2)

    def test_rejects_fake_human_claim_and_invalid_pairs(self):
        prov = json.loads(self.provenance.read_text())
        prov["reference_type"] = "independent_human"
        self.provenance.write_text(json.dumps(prov))
        self.assertEqual(self.cli().returncode, 2)
        prov["reference_type"] = "ai_assisted"
        self.provenance.write_text(json.dumps(prov))
        self.candidate_rows[0]["pairs"] = [pair("size"), pair("size")]
        self.write_rows(self.candidate, self.candidate_rows)
        self.assertEqual(self.cli().returncode, 2)

    def test_refuses_missing_candidate_row_and_unknown_id(self):
        self.write_rows(self.candidate, self.candidate_rows[:-1])
        self.assertEqual(self.cli().returncode, 2)
        self.write_rows(self.candidate, [*self.candidate_rows, record("alien", [])])
        self.assertEqual(self.cli().returncode, 2)

    def test_undefined_metrics_not_called_zero_or_success(self):
        ids = {"id"}
        src = {"id": {"product_hash": "one", "language": "en", "category": "apparel"}}
        r = M.evaluate(src, {"id": frozenset()}, {"id": frozenset()},
                       {"id": frozenset()}, {"annotator_model": "fixture",
                       "blind_to_predictions": True}, "D3")
        self.assertIsNone(r["task_metrics"]["candidate"]["T1"]["f1"])
        self.assertIsNone(r["task_metrics"]["candidate"]["T1"]["precision"])
        self.assertFalse(r["t1_all_three_at_least_080_on_this_proxy"])

    def test_f2_is_sealed_without_freeze_and_ledger(self):
        self.assertEqual(self.cli("F2").returncode, 2)
        self.assertFalse(self.out.exists())
        freeze = self.folder / "freeze.json"
        freeze.write_text(json.dumps({
            "accepted_csv_sha256": M.file_sha256(self.reviews),
            "candidate_commit_sha": "1" * 40,
            "baseline_commit_sha": "2" * 40,
            "rubric_sha256": "a" * 64,
            "frozen_before_final_reference": True,
            "feature_policy": "unchanged",
        }))
        ledger = self.folder / "final-ledger.json"
        self.assertEqual(self.cli("F2", ("--freeze", str(freeze))).returncode, 2)
        self.assertEqual(self.cli("F2", (
            "--freeze", str(freeze), "--final-ledger", str(ledger)
        )).returncode, 0)
        self.assertTrue(ledger.exists())
        self.assertEqual(self.cli("F2", (
            "--freeze", str(freeze), "--final-ledger", str(ledger)
        )).returncode, 2)

    def test_f2_must_match_exact_predeclared_source_and_rubric(self):
        freeze = self.folder / "freeze.json"
        ledger = self.folder / "ledger.json"
        base = {
            "accepted_csv_sha256": "f" * 64,
            "candidate_commit_sha": "1" * 40,
            "baseline_commit_sha": "2" * 40,
            "rubric_sha256": "a" * 64,
            "frozen_before_final_reference": True,
            "feature_policy": "unchanged",
        }
        freeze.write_text(json.dumps(base))
        self.assertEqual(self.cli("F2", ("--freeze", str(freeze), "--final-ledger", str(ledger))).returncode, 2)
        self.assertFalse(ledger.exists())
        base["accepted_csv_sha256"] = M.file_sha256(self.reviews)
        base["rubric_sha256"] = "f" * 64
        freeze.write_text(json.dumps(base))
        self.assertEqual(self.cli("F2", ("--freeze", str(freeze), "--final-ledger", str(ledger))).returncode, 2)
        self.assertFalse(ledger.exists())

    def test_no_real_data_can_reside_under_git_checkout(self):
        with self.assertRaises(M.ScoringError):
            M._check_off_repo(ROOT / "data.csv")
        self.assertTrue(M._outside_repo(self.reviews))

    def test_wilson_intervals_and_false_positive_counts(self):
        self.assertEqual(M.prf(2, 1, 1)["precision"], 0.6667)
        self.assertIsNone(M.prf(0, 0, 0)["recall_ci95"])
        self.assertEqual(M.prf(0, 1, 0)["f1"], 0)
        self.assertEqual(M._counter(
            frozenset([("product", "fit", "positive")]),
            frozenset([("product", "fit", "negative")]),
            "product"
        )["fp"], 1)


if __name__ == "__main__":
    unittest.main()
