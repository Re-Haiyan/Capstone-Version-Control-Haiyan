"""Unit tests for candidate-only training weights; no model inference."""
import importlib.util
import unittest
from pathlib import Path

path=Path(__file__).resolve().parents[1]/"research/xlmr_optimization/phase5/training_ablation_manifest.py"
spec=importlib.util.spec_from_file_location("phase5manifest",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ManifestTests(unittest.TestCase):
    def test_zero_weight_not_reported_as_label_repair(self):
        rows=[{"id":"N0001","split":"candidates","claude_v1_label":"neutral",
               "category":"disagreement","review_required":1,"language_hint":"english",
               "three_class_eligible":1,"baseline_weight":1.0,
               "exclude_disagreement_weight":0.0,"s4_downweight_sensitivity_weight":0.0}]
        result=m.summarize(rows)
        self.assertEqual(result["weights"]["baseline_weight"]["total_nonzero_rows"],1)
        self.assertEqual(result["weights"]["exclude_disagreement_weight"]["total_nonzero_rows"],0)
        self.assertIn("remain frozen Claude v1",result["not_reference_labels"])

    def test_low_weight_does_not_increase_effective_support(self):
        rows=[{"id":"N0002","split":"candidates","claude_v1_label":"neutral",
               "category":"tag_shape_uncertain","review_required":0,"language_hint":"english",
               "three_class_eligible":1,"baseline_weight":1.0,
               "exclude_disagreement_weight":1.0,"s4_downweight_sensitivity_weight":0.25}]
        out=m.summarize(rows)
        self.assertEqual(out["weights"]["s4_downweight_sensitivity_weight"]["effective_examples_by_label"]["neutral"],.25)

if __name__=="__main__":
    unittest.main()
