"""Check agreement math and prevent accidental editing or gold-standard claims."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1]/"research/xlmr_optimization/phase5/compare_second_ai.py"
spec=importlib.util.spec_from_file_location("second_ai_scoring", SCRIPT)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SecondAIAgreementTests(unittest.TestCase):
    def test_perfect_agreement(self):
        x=m.measure(["negative","neutral","positive"],["negative","neutral","positive"], m.LABELS[:3])
        self.assertEqual(x["cohens_kappa"],1)
        self.assertEqual(x["agreed"],3)

    def test_chance_adjusted_zero(self):
        x=m.measure(["positive","positive","neutral","neutral"],
                    ["positive","neutral","positive","neutral"],m.LABELS[:3])
        self.assertEqual(x["cohens_kappa"],0)

    def test_disagreement_confusion_orientation(self):
        x=m.measure(["neutral","neutral","positive"],["positive","neutral","positive"],m.LABELS[:3])
        self.assertEqual(x["confusion_rows_claude_columns_gpt6"][1][2],1)
        self.assertEqual(x["agreed"],2)

    def test_invalid_label_rejected(self):
        with self.assertRaises(ValueError):
            m.measure(["good"],["neutral"])


if __name__=="__main__":
    unittest.main()
