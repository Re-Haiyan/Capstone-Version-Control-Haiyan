"""Synthetic-only tests for Phase 4 blinded reference preparation.

No real buyer review text, frozen F2 labels, or model output is used in CI.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

PATH = (Path(__file__).resolve().parents[1] /
        "research/product_specific_conclusions/phase4/prepare_reference.py")
spec = importlib.util.spec_from_file_location("phase4_prepare_reference", PATH)
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


class Phase4ReferencePacketsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.intake = self.root / "intake"
        self.intake.mkdir()
        self.out = self.root / "reviewers"
        self.rows = {}
        for split, count, pfx in (("D3", 300, "aa"), ("V3", 150, "bb")):
            records = [{
                "review_id": f"{pfx}{i:04d}",
                "product_hash": f"{pfx}-prod-{i//10:03d}",
                "category": "sample_category", "group": "sample_group",
                "language": "taglish" if i % 3 == 0 else "en",
                "stars": str(1+i%5),
                "source_kind": "authorized_export",
                "source_id": "synthetic-test-only",
                "collection_date": "2026-11-15",
                "review_text": f"Synthetic sentence number {i}: ang item ay gumagana.",
            } for i in range(count)]
            self.rows[split] = records
            self.write(split, records)
        (self.intake/"manifest.json").write_text(json.dumps({
            "phase":"4", "method":"synthetic test fixture only",
            "research_ready":True,
            "counts":{"D3":300,"V3":150,"F2":200},
            "targets":{"D3":300,"V3":150,"F2":200},
            "product_counts":{"D3":30,"V3":15,"F2":20},
        }),encoding="utf-8")
        # Intentionally no F2 file anywhere. The workflow must not need or open it.

    def write(self, split, rows):
        with (self.intake / f"{split}.csv").open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(prep.INPUT_FIELDS))
            writer.writeheader()
            writer.writerows(rows)

    def test_two_blind_development_packets_no_f2(self):
        result = prep.build(self.intake,self.out)
        self.assertEqual(result["packet_row_counts"],{
            "D3_reviewer_A_BLIND.csv":300,
            "D3_reviewer_B_BLIND.csv":300,
        })
        self.assertFalse((self.out/"V3_reviewer_A_BLIND.csv").exists())
        self.assertEqual(len(list(self.out.glob("*.csv"))),2)
        a = list(csv.DictReader((self.out/"D3_reviewer_A_BLIND.csv").open()))
        b = list(csv.DictReader((self.out/"D3_reviewer_B_BLIND.csv").open()))
        self.assertEqual({x["review_id"] for x in a},{x["review_id"] for x in b})
        self.assertNotEqual([x["review_id"] for x in a],[x["review_id"] for x in b])
        self.assertEqual(len(a),300)
        for row in a:
            self.assertNotIn("stars",row)
            self.assertNotIn("source_id",row)
            self.assertNotIn("product_hash",row)
            self.assertEqual(row["features"],"")
            self.assertEqual(row["reviewer_id"],"")
            self.assertEqual(row["policy_version"],"")
            self.assertIn("Synthetic sentence",row["review_text"])
        self.assertEqual((self.out/"D3_reviewer_A_BLIND.csv").stat().st_mode & 0o777,0o600)
        self.assertNotIn("Synthetic sentence",(self.out/"packet_provenance.json").read_text())

    def test_explicitly_requested_validation_is_distinct(self):
        result = prep.build(self.intake,self.out,include_v3=True)
        self.assertEqual(len(result["packet_row_counts"]),4)
        self.assertEqual(result["split_product_counts"],{"D3":30,"V3":15})
        self.assertTrue((self.out/"V3_reviewer_B_BLIND.csv").is_file())

    def test_dry_run_never_writes_files(self):
        result = prep.build(self.intake,self.out,dry_run=True)
        self.assertEqual(result["status"].split(";")[0],"BLANK")
        self.assertFalse(self.out.exists())

    def test_no_invented_ready_status(self):
        manifest=self.intake/"manifest.json"
        m=json.loads(manifest.read_text())
        m["research_ready"]=False
        manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(prep.PacketError,"research-ready"):
            prep.build(self.intake,self.out)
        self.assertFalse(self.out.exists())

    def test_product_overlap_between_splits_is_rejected(self):
        v=self.rows["V3"]
        v[0]["product_hash"]=self.rows["D3"][0]["product_hash"]
        self.write("V3",v)
        with self.assertRaisesRegex(prep.PacketError,"Product-group leakage"):
            prep.build(self.intake,self.out)

    def test_duplicate_review_id_is_rejected(self):
        d=self.rows["D3"]
        d[1]["review_id"]=d[0]["review_id"]
        self.write("D3",d)
        with self.assertRaisesRegex(prep.PacketError,"duplicate review"):
            prep.build(self.intake,self.out)

    def test_no_reviewer_packet_overwrite(self):
        prep.build(self.intake,self.out)
        with self.assertRaisesRegex(prep.PacketError,"Output exists"):
            prep.build(self.intake,self.out)

    def test_intake_cannot_be_repository_directory(self):
        with self.assertRaisesRegex(prep.PacketError,"outside the public"):
            prep.validate_intake(prep.REPO)

    def test_f2_quota_not_optional(self):
        manifest=self.intake/"manifest.json"
        m=json.loads(manifest.read_text())
        m["counts"]["F2"]=0
        manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(prep.PacketError,"preregistered quotas"):
            prep.build(self.intake,self.out)

    def test_source_and_target_are_separate(self):
        with self.assertRaisesRegex(prep.PacketError,"separate directories"):
            prep.build(self.intake,self.intake/"results")


if __name__ == "__main__":
    unittest.main()
