"""The optional sentiment calibrator: off by default, safe on a bad path, and sensible on clear cases."""
import os, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import sentiment_calibration as sc  # noqa: E402

ARTIFACT = ROOT / "research" / "artifacts" / "sentiment_calibrator_v1.joblib"


class CalibratorTests(unittest.TestCase):
    def test_off_by_default(self):
        os.environ.pop(sc.ENV, None)
        self.assertIsNone(sc.load_default())

    def test_a_missing_or_bad_artifact_falls_back_to_none(self):
        os.environ[sc.ENV] = str(ROOT / "nope.joblib")
        try:
            self.assertIsNone(sc.load_default())
            bad = ROOT / "research" / "cache" / "bad.joblib"; bad.write_bytes(b"not a model")
            os.environ[sc.ENV] = str(bad)
            self.assertIsNone(sc.load_default())
            bad.unlink()
        finally:
            os.environ.pop(sc.ENV, None)

    @unittest.skipUnless(ARTIFACT.is_file(), "artifact not built")
    def test_clear_cases(self):
        cal = sc.SentimentCalibrator.load(ARTIFACT)
        pos, _ = cal.predict("Ang ganda ng product, sulit na sulit, very satisfied!", 5, {"negative": 0.02, "neutral": 0.08, "positive": 0.90})
        neg, _ = cal.predict("Sira agad, hindi gumana, sayang ang pera ko", 1, {"negative": 0.95, "neutral": 0.03, "positive": 0.02})
        self.assertEqual(pos, "positive")
        self.assertEqual(neg, "negative")

if __name__ == "__main__":
    unittest.main()
