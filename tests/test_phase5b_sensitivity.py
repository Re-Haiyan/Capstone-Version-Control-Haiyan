"""Phase 5B development-only lexical ablation safety tests."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "research/xlmr_optimization/phase5/phase5b_sensitivity.py"
spec = importlib.util.spec_from_file_location("phase5b_sensitivity", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Phase5BSafetyTests(unittest.TestCase):
    def test_group_titles(self):
        self.assertEqual(module.normalized_title("  Redmi A7 - Pro!! "), module.normalized_title("redmi a7 pro"))
        self.assertEqual(module.normalized_title("  "), "")

    def test_metrics(self):
        result = module.scores(["negative","neutral","positive"], ["negative","neutral","positive"])
        self.assertEqual(result["macro_f1"], 1.0)
        self.assertEqual(result["classes"]["neutral"]["f1"], 1.0)
        self.assertEqual(result["confusion"], [[1,0,0],[0,1,0],[0,0,1]])

    def test_empty_subset(self):
        result = module.scores([], [])
        self.assertEqual(result["n"], 0)
        self.assertIsNone(result["macro_f1"])

    def test_reviewed_product_title_groups_excluded_from_all_eval_strata(self):
        rows = [
            {"reviewed_group": True, "split": "dev", "tag_shape": False, "language": "taglish"},
            {"reviewed_group": True, "split": "candidates", "tag_shape": True, "language": "english"},
            {"reviewed_group": False, "split": "dev", "tag_shape": False, "language": "english"},
            {"reviewed_group": False, "split": "candidates", "tag_shape": True, "language": "filipino"},
        ]
        s = module.subsets(rows)
        for ids in s.values():
            self.assertTrue(all(i >= 2 for i in ids))
        self.assertEqual(s["all_unreviewed"], [2,3])
        self.assertEqual(s["natural_dev_unreviewed"], [2])
        self.assertEqual(s["filipino_taglish_unreviewed"], [3])

    def test_mismatched_predictions_rejected(self):
        with self.assertRaises(ValueError):
            module.scores(["positive"], [])


if __name__ == "__main__":
    unittest.main()
