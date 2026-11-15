"""Product-level batches for the card and words sheets. Synthetic fills only, inside temporary folders: they test the workflow and the refusals,
they are not annotations and their numbers say nothing about the system."""
import csv
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "product_specific_conclusions" / "ai_annotation"))
sys.path.insert(0, str(ROOT / "research" / "product_specific_conclusions"))
import batches as bt  # noqa: E402
import final_eval_pack as fp  # noqa: E402


def read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write(path, rows, cols):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


PROVENANCE = {"annotator": "synthetic test fixture", "model_version": "none", "interface": "test", "date": "test", "prompt_file": "none", "human_review_of_labels": "none"}


class Batches(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="batches-"))
        self.before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fp.PACK.iterdir()}
        self.out = self.tmp / "batches"
        self.key = {k["product_id"]: k for k in read(fp.PACK / "key_private.csv")}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def returned(self, cards=True, words=True, provenance=True):
        ret = self.tmp / "returned"
        ret.mkdir(exist_ok=True)
        bt.make(5, self.tmp / "b")
        for path in (self.tmp / "b").glob("*_return.csv"):
            data = read(path)
            if "card_return" in path.name and cards:
                for r in data:
                    r["assessment"] = self.key[r["product_id"]]["system_card"]
                    r["serious_safety_concern"] = "no"
                    r["counterfeit_concern"] = "no"
                    r["main_reason"] = "synthetic reason, not an actual annotation"
                    r["confidence"] = "medium"
            if "words_return" in path.name and words:
                for r in data:
                    for c in fp.CRITERIA:
                        for n in (1, 2):
                            r[f"{c}_{n}"] = "4"
                    for x in ("unsupported", "safety_error"):
                        for n in (1, 2):
                            r[f"{x}_{n}"] = "no"
                    r["preferred"] = "same"
            write(ret / path.name, data, list(data[0].keys()))
        if provenance:
            (ret / "provenance.json").write_text(json.dumps(PROVENANCE), encoding="utf-8")
        return ret

    def test_batches_cover_every_product_once_and_the_card_packets_show_no_system_output(self):
        n = bt.make(5, self.out)
        self.assertEqual(n, 7)
        ids = []
        for path in sorted(self.out.glob("batch_*_card_return.csv")):
            ids += [r["product_id"] for r in read(path)]
        self.assertEqual(sorted(ids), sorted(self.key))
        for packet in self.out.glob("batch_*_card_packet.md"):
            text = packet.read_text(encoding="utf-8")
            self.assertNotIn("Assessment shown", text, f"{packet.name} shows the system's assessment")
            for w in read(fp.PACK / "words_sheet_A.csv"):
                for shown in (w["text_1"], w["text_2"]):
                    self.assertNotIn(shown, text, f"{packet.name} shows a system text")
        self.assertIn("Assessment shown", (self.out / "batch_01_words_packet.md").read_text(encoding="utf-8"))

    def test_the_return_templates_are_blank(self):
        bt.make(5, self.out)
        for path in self.out.glob("batch_*_card_return.csv"):
            self.assertTrue(all(r["assessment"] == "" for r in read(path)))
        for path in self.out.glob("batch_*_words_return.csv"):
            self.assertTrue(all(r["factual_1"] == "" and r["preferred"] == "" for r in read(path)))

    def test_merge_refuses_without_provenance(self):
        with self.assertRaises(SystemExit):
            bt.merge(self.returned(provenance=False), self.tmp / "work")

    def test_an_untouched_batch_stays_pending_and_is_never_guessed(self):
        out = bt.merge(self.returned(cards=False, words=False), self.tmp / "work")
        self.assertEqual(out["card"]["products_returned"], 0)
        self.assertTrue(all(r["assessment"] == "" for r in read(self.tmp / "work" / "card_sheet_A.csv")))

    def test_words_before_cards_is_refused(self):
        with self.assertRaises(SystemExit):
            bt.merge(self.returned(cards=False, words=True), self.tmp / "work")

    def test_a_changed_prefilled_column_or_a_bad_value_is_refused(self):
        ret = self.returned()
        path = next(ret.glob("batch_01_card_return.csv"))
        data = read(path)
        data[0]["product"] = "something else"
        write(path, data, fp.CARD_COLS)
        with self.assertRaises(SystemExit):
            bt.merge(ret, self.tmp / "work")
        ret = self.returned()
        path = next(ret.glob("batch_01_words_return.csv"))
        data = read(path)
        data[0]["factual_1"] = "9"
        write(path, data, fp.WORDS_COLS)
        with self.assertRaises(SystemExit):
            bt.merge(ret, self.tmp / "work")

    def test_a_full_synthetic_return_merges_and_scores_in_single_mode_without_touching_the_pack(self):
        work = self.tmp / "work"
        bt.merge(self.returned(), work)
        out = fp.score(work)
        self.assertEqual(out["provenance"]["mode"], "single_annotation_set")
        self.assertEqual(out["card"]["system_vs_annotator_exact"][:2], [len(self.key), len(self.key)])
        self.assertEqual(out["words"]["products"], len(self.key))
        self.assertEqual(out["words"]["criteria"]["factual"]["mean_difference_new_minus_old"], 0.0)
        self.assertFalse(out["provenance"]["independent_human_evaluation_completed"])
        self.assertEqual({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fp.PACK.iterdir()}, self.before)

    def test_a_blank_card_sheet_makes_that_section_pending_not_an_error(self):
        work = self.tmp / "work"
        bt.merge(self.returned(cards=False, words=False), work)
        write(work / "claims_sheet_A.csv", read(fp.PACK / "claims_sheet_A.csv"), fp.CLAIM_COLS)
        for r in read(work / "claims_sheet_A.csv"):
            pass
        rows = read(work / "claims_sheet_A.csv")
        for r in rows:
            r["label"] = "correct"
        write(work / "claims_sheet_A.csv", rows, fp.CLAIM_COLS)
        out = fp.score(work)
        self.assertTrue(str(out["card"]).startswith("pending"))
        self.assertTrue(str(out["words"]).startswith("pending"))


    def test_partial_card_return_is_rejected_without_writing(self):
        ret = self.returned()
        path = ret / "batch_01_card_return.csv"
        data = read(path)
        data[0]["confidence"] = ""
        write(path, data, fp.CARD_COLS)
        work = self.tmp / "work"
        with self.assertRaises(SystemExit):
            bt.merge(ret, work)
        self.assertFalse((work / "card_sheet_A.csv").exists())

    def test_invalid_card_flags_and_preference_are_rejected(self):
        ret = self.returned()
        card = ret / "batch_01_card_return.csv"
        data = read(card)
        data[0]["serious_safety_concern"] = "maybe"
        write(card, data, fp.CARD_COLS)
        with self.assertRaises(SystemExit):
            bt.merge(ret, self.tmp / "work")
        data[0]["serious_safety_concern"] = "no"
        write(card, data, fp.CARD_COLS)
        words = ret / "batch_01_words_return.csv"
        w = read(words)
        w[0]["preferred"] = "both"
        write(words, w, fp.WORDS_COLS)
        with self.assertRaises(SystemExit):
            bt.merge(ret, self.tmp / "work")

    def test_late_invalid_words_batch_preserves_existing_outputs(self):
        work = self.tmp / "work"
        bt.merge(self.returned(), work)
        before = {name: hashlib.sha256((work / name).read_bytes()).hexdigest()
                  for name in ("card_sheet_A.csv", "words_sheet_A.csv", "provenance.json")}
        ret = self.returned()
        path = ret / "batch_07_words_return.csv"
        w = read(path)
        w[0]["safety_error_2"] = ""
        write(path, w, fp.WORDS_COLS)
        with self.assertRaises(SystemExit):
            bt.merge(ret, work)
        after = {name: hashlib.sha256((work / name).read_bytes()).hexdigest()
                 for name in before}
        self.assertEqual(after, before)

    def test_bad_header_is_rejected_and_locked_pack_never_targeted(self):
        ret = self.returned()
        path = ret / "batch_01_card_return.csv"
        data = read(path)
        write(path, data, list(reversed(fp.CARD_COLS)))
        with self.assertRaises(SystemExit):
            bt.merge(ret, self.tmp / "work")
        with self.assertRaises(SystemExit):
            bt.merge(ret, fp.PACK)
        self.assertFalse((self.tmp / "work" / "card_sheet_A.csv").exists())


if __name__ == "__main__":
    unittest.main()
