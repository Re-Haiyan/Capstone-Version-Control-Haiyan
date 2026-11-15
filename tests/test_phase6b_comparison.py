"""Phase 6B independent second-AI comparison, reproducibility and no-auto-apply."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT=(Path(__file__).resolve().parents[1]/
        "research/xlmr_optimization/phase6_annotation/compare_phase6b.py")
spec=importlib.util.spec_from_file_location("phase6b_compare",SCRIPT)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Phase6BCompareTests(unittest.TestCase):
    def test_perfect_kappa(self):
        x=m.agreement(["negative","neutral","positive"],["negative","neutral","positive"],m.LABELS[:3])
        self.assertEqual(x["agreed"],3)
        self.assertEqual(x["cohens_kappa"],1.0)

    def test_one_disagreement_confusion_orientation(self):
        x=m.agreement(["negative","neutral","positive"],["negative","positive","positive"],m.LABELS[:3])
        self.assertEqual(x["agreed"],2)
        self.assertEqual(x["confusion_rows_claude_columns_gpt6"][1][2],1)

    def test_invalid_class(self):
        with self.assertRaises(ValueError):
            m.agreement(["unhappy"],["neutral"])

    def test_real_second_ai_labels_have_exact_roster_and_overlay_is_proposed_only(self):
        # This checks the SOURCE-Locked development annotations, not frozen
        # test/confirmation content. No training weights are changed.
        data=m.compare()
        self.assertEqual(data["five_class"]["count"],54)
        self.assertEqual(sum(data["change_types"].values()),54)
        self.assertGreater(data["change_types"].get("sentiment",0),0)
        self.assertTrue(all(r["status"]=="proposed_not_adjudicated"
                            for r in data["overlays"]))
        self.assertTrue(all(not r["human_final_label"] for r in data["overlays"]))
        self.assertEqual(set(data["clear_evidence_review_priorities"]),
                         {"N2459","N2372","N1025","N1682"})

    def test_provenance_explicit_about_blindness_and_human_limit(self):
        data=m.compare()
        self.assertIn("partly blind",data["limits"][2])
        self.assertIn("not human adjudication",data["limits"][0])


if __name__=="__main__":
    unittest.main()
