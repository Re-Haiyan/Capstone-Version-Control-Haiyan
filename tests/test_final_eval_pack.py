"""The final independent-evaluation pack is blind, real, composed as promised, and scoring refuses without real annotations.

The scoring arithmetic is tested on SYNTHETIC filled sheets built inside a temporary folder. They are fixtures for the arithmetic only:
they are never written to the pack, their numbers are not evidence about the system, and no test here fills a real sheet.
"""
import csv
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "product_specific_conclusions"))
import final_eval_pack as fp  # noqa: E402

PACK = fp.PACK


def read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write(path, rows, cols):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


class Pack(unittest.TestCase):
    def setUp(self):
        self.key = read(PACK / "key_private.csv")
        self.card = {s: read(PACK / f"card_sheet_{s}.csv") for s in "AB"}
        self.claims = {s: read(PACK / f"claims_sheet_{s}.csv") for s in "AB"}
        self.words = {s: read(PACK / f"words_sheet_{s}.csv") for s in "AB"}

    def test_the_sheets_are_empty_for_the_annotators(self):
        for s in "AB":
            for row in self.card[s]:
                for column in fp.CARD_COLS[2:]:
                    self.assertEqual(row[column], "")
            for row in self.claims[s]:
                self.assertEqual((row["label"], row["note"]), ("", ""))
            for row in self.words[s]:
                for column in fp.WORDS_COLS[5:]:
                    self.assertEqual(row[column], "", column)

    def test_the_card_and_claim_sheets_show_no_system_output(self):
        self.assertEqual(list(self.card["A"][0].keys()), fp.CARD_COLS)
        self.assertNotIn("assessment_shown", self.card["A"][0])
        self.assertEqual(list(self.claims["A"][0].keys()), fp.CLAIM_COLS)
        text = " ".join(" ".join(r.values()) for r in self.card["A"] + self.card["B"])
        for system_words in ("Well reviewed", "Some concerns", "Not recommended", "Mixed reviews", "Too few reviews"):
            self.assertNotIn(system_words, text, "the system's card name is on a sheet the annotator fills before seeing it")

    def test_the_words_sheet_does_not_say_which_text_is_new(self):
        for s in "AB":
            for row in self.words[s]:
                self.assertNotIn("old", (row["text_1"], row["text_2"]))
                self.assertNotIn("new", (row["text_1"], row["text_2"]))
                self.assertNotEqual(row["text_1"], row["text_2"])
        order = {(k["text_1"], k["text_2"]) for k in self.key}
        self.assertEqual(order, {("old", "new"), ("new", "old")}, "the new text is not always in the same position")

    def test_same_items_different_order_for_the_two_annotators(self):
        for sheets, col in ((self.card, "product_id"), (self.claims, "claim_id"), (self.words, "product_id")):
            self.assertEqual({r[col] for r in sheets["A"]}, {r[col] for r in sheets["B"]})
            self.assertNotEqual([r[col] for r in sheets["A"]], [r[col] for r in sheets["B"]])

    def test_the_sample_is_composed_as_promised_and_is_not_only_easy_cases(self):
        self.assertGreaterEqual(len(self.key), fp.MIN_PRODUCTS)
        self.assertEqual({k["system_card"] for k in self.key}, set(fp.CARDS), "every assessment is present")
        self.assertGreaterEqual(sum(1 for k in self.key if int(k["safety_reports"])), 5)
        self.assertGreaterEqual(sum(1 for k in self.key if int(k["authenticity_reports"])), 5)
        self.assertGreaterEqual(sum(1 for k in self.key if float(k["filipino_or_taglish_share"]) >= 0.25), 10)
        self.assertGreaterEqual(sum(1 for k in self.key if k["pool"].startswith("real non-electronics")), 10, "real non-electronics products that were not read while tuning")
        self.assertGreaterEqual(len(self.claims["A"]), fp.MIN_CLAIMS)

    def test_the_reviews_file_has_every_product_and_no_reviewer(self):
        reviews = read(PACK / "reviews.csv")
        self.assertEqual(list(reviews[0].keys()), ["product_id", "review_no", "stars", "review_text"])
        self.assertEqual({r["product_id"] for r in reviews}, {k["product_id"] for k in self.key})

    def test_no_personal_contact_detail_is_in_anything_annotators_receive(self):
        """Found by the pre-commit scan: a Philippine mobile number was typed into one review. Phone numbers, e-mails, links and handles are removed."""
        import re

        patterns = {
            "mobile number": r"(?<!\d)(?:\+?63|0)\s?9\d{2}[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)",
            "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            "link": r"https?://|www\.",
            "handle": r"(?<![\w])@[A-Za-z0-9_.]{4,}",
            "long number": r"(?<!\d)\d{9,}(?!\d)",
        }
        texts = [r["review_text"] for r in read(PACK / "reviews.csv")] + [c["quotation"] for s in "AB" for c in self.claims[s]]
        for name, pattern in patterns.items():
            self.assertEqual([t[:60] for t in texts if re.search(pattern, t)], [], name)

    def test_redaction_removes_what_it_says_and_nothing_else(self):
        self.assertEqual(fp.redact("call 09123456789 now"), "call [number removed] now")
        self.assertEqual(fp.redact("text +63 917 123 4567 or 0917-123-4567"), "text [number removed] or [number removed]")
        self.assertEqual(fp.redact("mail me at juan_dela.cruz@example.com"), "mail me at [email removed]")
        self.assertEqual(fp.redact("see https://fb.com/x and www.shop.ph"), "see [link removed] and [link removed]")
        self.assertEqual(fp.redact("Ang lambot ng buhok ko, 5 stars, 2 weeks, 100% legit"), "Ang lambot ng buhok ko, 5 stars, 2 weeks, 100% legit")

    def test_claims_point_at_real_review_text(self):
        reviews = {(r["product_id"], r["review_no"]): r["review_text"] for r in read(PACK / "reviews.csv")}
        found = 0
        for claim in self.claims["A"]:
            text = reviews.get((claim["product_id"], claim["review_no"]))
            self.assertIsNotNone(text, claim["claim_id"])
            body = claim["quotation"].rstrip("…").rstrip()
            self.assertIn(body, text, claim["claim_id"])
            found += 1
        self.assertGreaterEqual(found, fp.MIN_CLAIMS)

    def test_scoring_refuses_without_real_annotations(self):
        with self.assertRaises(SystemExit):
            fp.score(PACK)


class Scoring(unittest.TestCase):
    """Arithmetic only, on synthetic sheets inside a temporary folder."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pack-score-"))
        self.key = {k["product_id"]: k for k in read(PACK / "key_private.csv")}
        self.before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in PACK.iterdir()}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fill(self, annotator, card=lambda k: k["system_card"], claim="correct", new=5, old=3, safety_error="no"):
        rows = read(PACK / "card_sheet_A.csv")
        for r in rows:
            r["assessment"] = card(self.key[r["product_id"]])
            r["serious_safety_concern"] = "no"
            r["counterfeit_concern"] = "no"
        write(self.tmp / f"card_sheet_{annotator}.csv", rows, fp.CARD_COLS)
        rows = read(PACK / "claims_sheet_A.csv")
        for r in rows:
            r["label"] = claim
        write(self.tmp / f"claims_sheet_{annotator}.csv", rows, fp.CLAIM_COLS)
        rows = read(PACK / "words_sheet_A.csv")
        for r in rows:
            k = self.key[r["product_id"]]
            for n in (1, 2):
                for c in fp.CRITERIA:
                    r[f"{c}_{n}"] = str(new if k[f"text_{n}"] == "new" else old)
                r[f"unsupported_{n}"] = "no"
                r[f"safety_error_{n}"] = safety_error if k[f"text_{n}"] == "new" else "no"
            r["preferred"] = "1" if k["text_1"] == "new" else "2"
        write(self.tmp / f"words_sheet_{annotator}.csv", rows, fp.WORDS_COLS)

    def test_perfect_agreement_gives_the_expected_numbers(self):
        self.fill("A")
        self.fill("B")
        out = fp.score(self.tmp)
        self.assertEqual(out["card"]["annotators_cohens_kappa"], 1.0)
        self.assertEqual(out["card"]["system_vs_annotator_A_exact"][0], out["card"]["products"])
        self.assertEqual(out["claims"]["strict_precision_both_say_correct"][0], out["claims"]["claims"])
        self.assertEqual(out["words"]["criteria"]["factual"]["mean_difference_new_minus_old"], 2.0)
        self.assertEqual(out["words"]["criteria"]["factual"]["quadratic_weighted_kappa"], 1.0)
        self.assertEqual(out["words"]["unsupported_rate_new_text"][0], 0)
        self.assertEqual(out["words"]["safety_error_rate_new_text"][0], 0)
        self.assertEqual(out["words"]["preferred"], {"new": 2 * out["words"]["products"]})

    def test_disagreement_and_safety_errors_are_counted(self):
        self.fill("A", claim="correct", safety_error="yes")
        self.fill("B", claim="wrong_direction", card=lambda k: "Not recommended")
        out = fp.score(self.tmp)
        self.assertEqual(out["claims"]["factual_claim_precision_annotator_B"][0], 0)
        self.assertEqual(out["claims"]["strict_precision_both_say_correct"][0], 0)
        self.assertEqual(out["words"]["safety_error_rate_new_text"][0], out["words"]["products"], "annotator A flagged every new text")
        self.assertLess(out["card"]["annotators_cohens_kappa"], 1.0)

    def test_scoring_needs_enough_complete_rows_from_both(self):
        self.fill("A")
        self.fill("B")
        rows = read(self.tmp / "card_sheet_B.csv")
        for r in rows[: len(rows) - (fp.MIN_PRODUCTS - 1)]:
            r["assessment"] = ""
        write(self.tmp / "card_sheet_B.csv", rows, fp.CARD_COLS)
        with self.assertRaises(SystemExit):
            fp.score(self.tmp)

    def test_scoring_never_writes_into_the_pack(self):
        self.fill("A")
        self.fill("B")
        fp.score(self.tmp)
        self.assertEqual({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in PACK.iterdir()}, self.before)

    def test_agreement_statistics_on_known_cases(self):
        self.assertAlmostEqual(fp.kappa(list("aabb"), list("abab")), 0.0)
        self.assertAlmostEqual(fp.kappa(list("aabb"), list("aabb")), 1.0)
        self.assertAlmostEqual(fp.weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]), 1.0)
        low, high = fp.wilson(90, 100)
        self.assertAlmostEqual(low, 0.826, places=2)
        self.assertAlmostEqual(high, 0.945, places=2)
        self.assertTrue(all(map(lambda v: v != v, fp.wilson(0, 0))), "no claims, no interval")


if __name__ == "__main__":
    unittest.main()
