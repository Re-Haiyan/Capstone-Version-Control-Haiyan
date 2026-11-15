"""Review-submission validation must never alter the source annotation sheets."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

PATH=(Path(__file__).resolve().parents[1]/
      "research/xlmr_optimization/phase6_annotation/review_submission.py")
spec=importlib.util.spec_from_file_location("phase6_review_submission",PATH)
review=importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)
        self.original=self.path/"blank.csv"
        self.completed=self.path/"completed.csv"
        self.row={
            "id":"D001","split":"dev","product":"Mouse","platform":"Lazada PH",
            "language_hint":"filipino","review_text":"Hindi gumagana ang mouse.",
            "sentiment":"","tags":"","positive_aspect":"","negative_aspect":"",
            "confidence":"","rationale":"","reviewer_id":"","reviewer_type":"",
            "policy_version":"",
        }
        self.write(self.original,self.row)

    def write(self,path,row):
        with path.open("w",newline="",encoding="utf-8") as file:
            writer=csv.DictWriter(file,fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)

    def test_valid_review_kept_separate(self):
        edited=dict(self.row,sentiment="negative",confidence="high",
                    rationale="explicitly reports failure",
                    reviewer_id="A03",reviewer_type="human",policy_version="v1")
        self.write(self.completed,edited)
        results=review.parse(self.original,self.completed)
        self.assertEqual(results[0]["sentiment"],"negative")
        self.assertEqual(results[0]["status"],"proposed_not_adjudicated")
        self.assertEqual(review.records(self.original)["D001"]["sentiment"],"")

    def test_tampered_original_text_rejected(self):
        edited=dict(self.row,review_text="different",sentiment="negative",
                    confidence="high",rationale="defect",
                    reviewer_id="A03",reviewer_type="human",policy_version="v1")
        self.write(self.completed,edited)
        with self.assertRaisesRegex(ValueError,"immutable source field edited"):
            review.parse(self.original,self.completed)

    def test_no_unattributed_ai_or_human_golden_labels(self):
        edited=dict(self.row,sentiment="positive",confidence="high",rationale="great",
                    reviewer_id="",reviewer_type="",policy_version="v1")
        self.write(self.completed,edited)
        with self.assertRaisesRegex(ValueError,"reviewer ID/type"):
            review.parse(self.original,self.completed)

    def test_unchanged_blind_rows_not_imported(self):
        self.write(self.completed,self.row)
        self.assertEqual(review.parse(self.original,self.completed),[])

    def test_mixed_requires_evidence(self):
        edited=dict(self.row,sentiment="mixed",tags="mixed",
                    confidence="high",rationale="good and bad",reviewer_id="A03",
                    reviewer_type="human",policy_version="v1")
        self.write(self.completed,edited)
        with self.assertRaisesRegex(ValueError,"mixed needs both aspects"):
            review.parse(self.original,self.completed)


if __name__=="__main__":
    unittest.main()
