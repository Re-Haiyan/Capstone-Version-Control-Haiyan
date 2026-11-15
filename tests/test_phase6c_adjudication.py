"""Phase 6C: all tests use invented review text; no real review labels."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

PATH = (Path(__file__).resolve().parents[1] /
        "research/xlmr_optimization/phase6_annotation/adjudication_gate.py")
spec = importlib.util.spec_from_file_location("phase6c_adjudication", PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class AdjudicationGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.blind = self.dir / "blind.csv"
        self.a = self.dir / "a.csv"
        self.b = self.dir / "b.csv"
        self.completed = self.dir / "adjudicated.csv"
        self.sources = [
            self.row("D001", "Charger stopped working after two days"),
            self.row("D002", "It works well and fast"),
            self.row("D003", "Okay lang"),
        ]
        self.write(self.blind, self.sources)
        self.write(self.a, [
            self.label(self.sources[0], "A01", "negative"),
            self.label(self.sources[1], "A01", "positive"),
            self.label(self.sources[2], "A01", "neutral"),
        ])
        self.write(self.b, [
            self.label(self.sources[0], "A02", "positive"),
            self.label(self.sources[1], "A02", "positive"),
            self.label(self.sources[2], "A02", "neutral", confidence="low"),
        ])

    def row(self, rid, review):
        return {
            "id": rid, "split": "dev", "product": "Example product",
            "platform": "Lazada PH", "language_hint": "english",
            "review_text": review, "sentiment": "", "tags": "",
            "positive_aspect": "", "negative_aspect": "", "confidence": "",
            "rationale": "", "reviewer_id": "", "reviewer_type": "",
            "policy_version": "",
        }

    def label(self, row, person, sentiment, confidence="high", kind="human", policy="v1"):
        return dict(row, sentiment=sentiment, confidence=confidence,
                    rationale="Opinion explicitly expressed", reviewer_id=person,
                    reviewer_type=kind, policy_version=policy)

    def write(self, path, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def completed_sheet(self, items, person="A03"):
        output = []
        for x in items:
            row = dict(x)
            row.update(
                final_sentiment="negative" if row["id"] == "D001" else "neutral",
                final_tags="",
                final_positive_aspect="", final_negative_aspect="",
                final_confidence="high",
                adjudication_rationale="Explicit statements in original review",
                evidence_quote="Charger stopped working" if row["id"] == "D001" else "Okay lang",
                adjudicator_id=person, adjudicator_type="human",
                policy_version="v1", adjudication_date="2026-11-15"
            )
            output.append(row)
        self.write(self.completed, output)
        return output

    def test_prepare_requires_unique_self_reported_human_reviewers(self):
        summary, questions = gate.prepare(self.blind, self.a, self.b)
        self.assertEqual(summary["both_completed"], 3)
        self.assertEqual(summary["needs_adjudication"], 2)
        self.assertEqual({r["id"] for r in questions}, {"D001", "D003"})
        self.assertEqual(summary["agreement"]["identical_sentiment"], 2)
        self.assertEqual(summary["reasons"]["low_confidence"], 1)
        self.assertIn("sentiment", summary["reasons"])
        self.assertEqual(summary["agreement"]["confusion_rows_reviewer_A_columns_reviewer_B"][0][2], 1)

    def test_rejects_same_person_twice(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            gate.prepare(self.blind, self.a, self.a)

    def test_rejects_ai_as_human_reviewer(self):
        b = [self.label(row, "Claude_AI", "neutral", kind="ai") for row in self.sources]
        self.write(self.b, b)
        with self.assertRaisesRegex(ValueError, "cannot use an AI"):
            gate.prepare(self.blind, self.a, self.b)

    def test_rejects_unapproved_policy_version(self):
        b = [self.label(row, "A02", "neutral", policy="v2-draft") for row in self.sources]
        self.write(self.b, b)
        with self.assertRaisesRegex(ValueError, "[Aa]pproved policy v1"):
            gate.prepare(self.blind, self.a, self.b)

    def test_rejects_tampered_source_text(self):
        a = [self.label(row, "A01", "negative") for row in self.sources]
        a[0]["review_text"] = "Different item instead"
        self.write(self.a, a)
        with self.assertRaisesRegex(ValueError, "immutable source"):
            gate.prepare(self.blind, self.a, self.b)

    def test_no_cherry_picked_partial_review_without_explicit_permission(self):
        a = [self.label(row, "A01", "negative") for row in self.sources[:-1]]
        self.write(self.a, a)
        with self.assertRaisesRegex(ValueError, "missing IDs"):
            gate.prepare(self.blind, self.a, self.b)
        info, _ = gate.prepare(self.blind, self.a, self.b, allow_partial=True)
        self.assertEqual(info["a_completed"], 2)
        self.assertEqual(info["no_pairwise_answer"], 1)

    def test_rejects_prelabelled_nonblind_packet(self):
        corrupted = [dict(row) for row in self.sources]
        corrupted[0]["sentiment"] = "neutral"
        self.write(self.blind, corrupted)
        with self.assertRaisesRegex(ValueError, "not blind"):
            gate.prepare(self.blind, self.a, self.b)

    def test_finalize_still_never_certifies_training_gold(self):
        summary, questions = gate.prepare(self.blind, self.a, self.b)
        self.completed_sheet(questions)
        output = gate.finalize(self.blind, self.a, self.b, self.completed)
        self.assertEqual(output["summary"]["rows_adjudicated_self_reported"], 2)
        self.assertFalse(output["summary"]["training_approved"])
        self.assertTrue(all(r["approved_for_training"] == "false" for r in output["rows"]))
        self.assertEqual(
            {r["status"] for r in output["rows"]},
            {"self_reported_adjudication_pending_identity_and_protocol_verification"}
        )
        self.assertEqual(gate.read_csv(self.blind)["D001"]["sentiment"], "")

    def test_adjudicator_cannot_be_reviewer(self):
        _, questions = gate.prepare(self.blind, self.a, self.b)
        self.completed_sheet(questions, person="A01")
        with self.assertRaisesRegex(ValueError, "must differ"):
            gate.finalize(self.blind, self.a, self.b, self.completed)

    def test_adjudicator_cannot_be_ai(self):
        _, questions = gate.prepare(self.blind, self.a, self.b)
        final = self.completed_sheet(questions)
        final[0]["adjudicator_type"] = "ai"
        self.write(self.completed, final)
        with self.assertRaisesRegex(ValueError, "self-identify as human"):
            gate.finalize(self.blind, self.a, self.b, self.completed)

    def test_adjudicator_must_quote_original_exactly(self):
        _, questions = gate.prepare(self.blind, self.a, self.b)
        final = self.completed_sheet(questions)
        final[0]["evidence_quote"] = "invented evidence"
        self.write(self.completed, final)
        with self.assertRaisesRegex(ValueError, "exact span"):
            gate.finalize(self.blind, self.a, self.b, self.completed)

    def test_adjudicator_cannot_modify_evidence(self):
        _, questions = gate.prepare(self.blind, self.a, self.b)
        final = self.completed_sheet(questions)
        final[0]["reviewer_b_sentiment"] = "negative"
        self.write(self.completed, final)
        with self.assertRaisesRegex(ValueError, "reviewer evidence was changed"):
            gate.finalize(self.blind, self.a, self.b, self.completed)

    def test_all_disagreements_required_at_finalization(self):
        _, questions = gate.prepare(self.blind, self.a, self.b)
        self.completed_sheet(questions[:1])
        with self.assertRaisesRegex(ValueError, "no additions or omissions"):
            gate.finalize(self.blind, self.a, self.b, self.completed)

    def test_future_adjudication_date_rejected(self):
        _, questions = gate.prepare(self.blind, self.a, self.b)
        final = self.completed_sheet(questions)
        final[0]["adjudication_date"] = "2099-12-01"
        self.write(self.completed, final)
        with self.assertRaisesRegex(ValueError, "cannot be in the future"):
            gate.finalize(self.blind, self.a, self.b, self.completed)

    def test_unattributed_adjudication_rejected(self):
        _, questions = gate.prepare(self.blind, self.a, self.b)
        final = self.completed_sheet(questions)
        final[0]["adjudicator_id"] = ""
        self.write(self.completed, final)
        with self.assertRaisesRegex(ValueError, "must differ"):
            gate.finalize(self.blind, self.a, self.b, self.completed)


if __name__ == "__main__":
    unittest.main()
