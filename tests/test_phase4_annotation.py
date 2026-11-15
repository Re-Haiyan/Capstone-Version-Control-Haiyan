"""Phase 4 (neutral recovery): annotation completeness, provenance wording, label validity, helper parsing and lock integrity.
These tests read the committed annotation files; the product-grouped-split test reads git-ignored private maps and is skipped when they are absent."""
import collections, csv, hashlib, json, pathlib, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
X = ROOT / "research" / "xlmr_optimization"
A = X / "annotation"
sys.path.insert(0, str(X))
import claude_annotation_helper as helper  # noqa: E402
import sentiment_agreement as sa  # noqa: E402


def rows(name):
    return list(csv.DictReader(open(A / "ai_labelled" / name, encoding="utf-8-sig")))


class CandidateAnnotation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = rows("neutral_candidate_pool_ai_v1.csv")

    def test_all_3000_candidates_labelled_once(self):
        ids = [x["id"] for x in self.r]
        self.assertEqual(len(ids), 3000)
        self.assertEqual(len(set(ids)), 3000)
        self.assertTrue(all(x["sentiment"] in ("positive", "neutral", "negative", "mixed", "unclear") for x in self.r))

    def test_every_label_passes_policy_v1_rules(self):
        bad = [p for x in self.r for p in sa.row_problems(x)]
        self.assertEqual(bad, [])

    def test_candidates_are_not_assumed_neutral(self):
        c = collections.Counter(x["sentiment"] for x in self.r)
        self.assertGreater(c["positive"], 500)
        self.assertGreater(c["negative"], 100)
        self.assertLess(c["neutral"], 3000)

    def test_no_opinion_tag_only_on_neutral_or_unclear(self):
        for x in self.r:
            if "no-opinion" in x["tags"]:
                self.assertIn(x["sentiment"], ("neutral", "unclear"))

    def test_returned_batches_cover_every_candidate_once(self):
        seen = collections.Counter()
        for f in (A / "claude_returns").glob("neutral_candidates_batch_*_returned.csv"):
            for x in csv.DictReader(open(f, encoding="utf-8-sig")):
                seen[x["id"]] += 1
        self.assertEqual(len(seen), 3000)
        self.assertEqual(max(seen.values()), 1)


class Provenance(unittest.TestCase):
    def test_log_says_claude_not_chatgpt_for_every_candidate_batch(self):
        log = list(csv.DictReader(open(A / "ai_annotation_log.csv", encoding="utf-8")))
        cand = [x for x in log if x["sheet"] == "neutral_candidate_pool.csv"]
        self.assertEqual(sum(int(x["rows"]) for x in cand), 3000)
        for x in cand:
            self.assertIn("Claude", x["model_as_stated_by_submitter"])
            self.assertIn("NOT ChatGPT", x["model_as_stated_by_submitter"])

    def test_provenance_file_states_claude_and_the_truncation_limitation(self):
        t = (A / "ai_labelled" / "PROVENANCE.md").read_text(encoding="utf-8")
        self.assertIn("None of these rows was labelled by ChatGPT", t)
        self.assertIn("3,000 of 3,000", t)
        self.assertIn("truncated", t)


class HelperParsing(unittest.TestCase):
    def test_codes_and_defaults(self):
        e = helper.parse("P: N0001 N0002; Ng: N0003; Nl: N0004; U: N0005; Dp: N0006; X:N0007=fast/slow=mixed")
        self.assertEqual(e["N0001"][0], "positive")
        self.assertEqual(e["N0003"][0], "negative")
        self.assertEqual(e["N0004"][:2], ("neutral", ""))
        self.assertEqual(e["N0005"][0], "unclear")
        self.assertEqual(e["N0006"][:2], ("positive", "delivery-only"))
        self.assertEqual(e["N0007"][:4], ("mixed", "mixed", "fast", "slow"))

    def test_mixed_rows_carry_both_aspects(self):
        e = helper.parse("X:N0100=good/bad=positive")
        self.assertEqual(e["N0100"][0], "positive")
        self.assertTrue(e["N0100"][2] and e["N0100"][3])


class Lock(unittest.TestCase):
    def test_phase4_artifacts_match_the_lock(self):
        lock = json.load(open(X / "phase4_lock.json"))
        for k in ("P4A", "P4B"):
            p = ROOT / lock[k]["artifact"]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), lock[k]["sha256"])
        self.assertFalse(lock["confirmation_set_used_in_training_or_selection"])
        self.assertFalse(lock["frozen_test_and_heldout_v2_used"])
        self.assertTrue(lock["shipped_model_unchanged"])


@unittest.skipUnless((A / "PRIVATE_neutral_candidate_map.csv").exists() and (A / "PRIVATE_id_map.csv").exists(), "private product maps are git-ignored")
class Split(unittest.TestCase):
    def test_product_grouped_folds_do_not_share_products(self):
        import numpy as np
        from sklearn.model_selection import StratifiedGroupKFold
        import phase3_experiments as p3
        rs = [r for r in p3.v1_rows() if r["label"] in ("negative", "neutral", "positive")]
        y = np.array([("negative", "neutral", "positive").index(r["label"]) for r in rs]); g = np.array([r["group"] for r in rs])
        for seed in (11, 12, 13):
            for tr, te in StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(np.zeros(len(rs)), y, g):
                self.assertFalse(set(g[tr]) & set(g[te]))


if __name__ == "__main__":
    unittest.main()
