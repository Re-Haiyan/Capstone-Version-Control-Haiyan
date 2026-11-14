"""The agreement statistics, checked on small hand-computed cases (no real annotations are used)."""
import pathlib, sys, unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "research"))
import agreement  # noqa: E402


class AgreementMath(unittest.TestCase):
    def test_perfect_agreement(self):
        a = np.array([1, 0, 1, 0, 1, 0])
        self.assertAlmostEqual(agreement.kappa(a, a), 1.0)
        self.assertAlmostEqual(agreement.stats(a, a)["raw_agreement"], 1.0)

    def test_hand_computed_kappa(self):
        # 10 reviews: both yes 4, A only 1, B only 1, both no 4 -> po 0.8, pe 0.5, kappa 0.6
        a = np.array([1] * 4 + [1] + [0] + [0] * 4)
        b = np.array([1] * 4 + [0] + [1] + [0] * 4)
        self.assertAlmostEqual(agreement.kappa(a, b), 0.6)
        s = agreement.stats(a, b)
        self.assertAlmostEqual(s["positive_agreement"], 2 * 4 / (2 * 4 + 2))
        self.assertEqual(s["confusion"], {"both_yes": 4, "A_only": 1, "B_only": 1, "both_no": 4})

    def test_ac1_is_defined_when_one_class_dominates(self):
        a = np.array([0] * 19 + [1]); b = np.array([0] * 19 + [0])
        self.assertTrue(agreement.ac1(a, b) > 0.9)

    def test_score_refuses_without_two_completed_sheets(self):
        with self.assertRaises(SystemExit):
            agreement.score(str(agreement.OUT / "sheet_A.csv"), str(agreement.OUT / "sheet_B.csv"))


if __name__ == "__main__":
    unittest.main()
