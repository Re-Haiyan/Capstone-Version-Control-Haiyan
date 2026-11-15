"""Phase 6 annotation integrity and blind-review privacy regression tests."""
from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] /
          "research/xlmr_optimization/phase6_annotation/annotation_quality.py")
spec=importlib.util.spec_from_file_location("phase6_annotation_quality",SCRIPT)
qa=importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


def original(rid="D000"):
    return {
        "id":rid,"product":"Test phone","category_group":"electronics",
        "platform":"Lazada PH","language_hint":"taglish",
        "review_text":"Hindi gumagana ang screen, sira pagdating.",
        "sentiment":"","tags":"","positive_aspect":"","negative_aspect":"",
        "confidence":"","rationale":"",
    }


def annotated(rid="D000"):
    return dict(original(rid),sentiment="neutral",tags="no-opinion",
                confidence="low",rationale="not tested")


def row(label="neutral",flags=None,group="a",rid="D000"):
    return {
        "id":rid,"split":"dev","label":label,"confidence":"low",
        "tags":"no-opinion" if label=="neutral" else "","language":"taglish",
        "product_group_title":group,"title":"Test phone",
        "platform":"Lazada PH","review_text":"Hindi gumagana ang screen.",
        "gpt6_label":"negative" if label=="neutral" else "",
        "flags":flags if flags is not None else ["ai_disagreement"],
        "score":qa.score(flags if flags is not None else ["ai_disagreement"]),
        "priority":qa.priority(qa.score(flags if flags is not None else ["ai_disagreement"])),
        "risk_info":{"list_shape":False},
        "verification_status":"unverified_ai_label",
    }


class Phase6AnnotationTests(unittest.TestCase):
    def test_detects_negative_cue_without_overwriting_label(self):
        r=annotated()
        flags=qa.flags_for(r,None,qa.shape(r["review_text"]))
        self.assertIn("negative_cue_in_no_opinion",flags)
        self.assertEqual(r["sentiment"],"neutral")

    def test_battery_endurance_praise_is_not_defect(self):
        good=annotated()
        good["review_text"]="Ang ganda ng item at matagal malowbat."
        self.assertNotIn("negative_cue_in_no_opinion",
                         qa.flags_for(good,None,qa.shape(good["review_text"])))
        bad=annotated()
        bad["review_text"]="Madaling malowbat ang battery."
        self.assertIn("negative_cue_in_no_opinion",
                      qa.flags_for(bad,None,qa.shape(bad["review_text"])))

    def test_damaged_replacement_descriptions_are_not_product_defects(self):
        row=annotated()
        row["review_text"]="Convenient replacement for damaged lids, fits a bottle."
        self.assertNotIn("negative_cue_in_no_opinion",
                         qa.flags_for(row,None,qa.shape(row["review_text"])))
        row["review_text"]="The item arrived damaged, hindi gumagana."
        self.assertIn("negative_cue_in_no_opinion",
                      qa.flags_for(row,None,qa.shape(row["review_text"])))

    def test_label_format_checks_no_opinion_and_aspects(self):
        qa.validate_pair({"D000":original()},{"D000":annotated()},"dev",1)
        wrong=annotated();wrong["sentiment"]="positive"
        with self.assertRaises(ValueError):
            qa.validate_pair({"D000":original()},{"D000":wrong},"dev",1)

    def test_detects_source_text_mutation(self):
        wrong=annotated();wrong["review_text"]="changed"
        with self.assertRaisesRegex(ValueError,"original review_text changed"):
            qa.validate_pair({"D000":original()},{"D000":wrong},"dev",1)

    def test_priority_review_always_keeps_ai_conflicts(self):
        a=[row(rid=f"D{i:03d}",group="same") for i in range(71)]
        b=[row(label="positive",flags=[],group=f"other-{i}",rid=f"N{i:04d}") for i in range(150)]
        selected=qa.select_priority_review(a+b,maximum=140,cap_per_title=3)
        self.assertEqual(len({r["id"] for r in selected}),len(selected))
        self.assertEqual(sum("ai_disagreement" in r["flags"] for r in selected),71)

    def test_random_annotation_quality_sample_is_reproducible(self):
        samples=[row(label="positive",flags=[],group=f"title-{i}",rid=f"N{i:04d}")
                 for i in range(300)]
        a=qa.select_random_quality_sample(samples,maximum=80)
        b=qa.select_random_quality_sample(list(reversed(samples)),maximum=80)
        self.assertEqual([r["id"] for r in a],[r["id"] for r in b])
        self.assertEqual(len(set(r["id"] for r in a)),80)

    def test_blind_packet_has_no_existing_labels_or_model_results(self):
        r=qa.blind_row(row())
        self.assertEqual(r["sentiment"],"")
        self.assertNotIn("gpt6_label",r)
        self.assertNotIn("flags",r)
        self.assertNotIn("risk_score",r)
        self.assertEqual(r["review_text"],"Hindi gumagana ang screen.")

    def test_public_default_does_not_export_full_text_packets(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            data=[row(label="positive",flags=[],rid=f"D{i:03d}",group=f"group_{i}") for i in range(150)]
            output=qa.emit(data,p,protected=13,maximum=140)
            self.assertFalse((p/"all_3400_blind_review.csv").exists())
            self.assertFalse((p/"priority_blind_review.csv").exists())
            self.assertFalse((p/"random_blind_review.csv").exists())
            self.assertTrue((p/"random_quality_sample_ids.csv").exists())
            self.assertTrue((p/"priority_ids.csv").exists())
            self.assertEqual(output["full_blind_review_packet_rows"],0)
            self.assertEqual(output["eligible_for_local_blind_export"],150)

    def test_protected_blob_hash_detects_mutation_without_reading_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            a=p/"frozen.csv";a.write_bytes(b"frozen,not,used\n")
            manifest=p/"blobs.json"
            manifest.write_text(json.dumps({"protected_blob_shas":{"frozen.csv":qa.git_blob_sha(a)}}))
            self.assertEqual(qa.verify_protected(p,manifest),1)
            a.write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError,"Protected source modified"):
                qa.verify_protected(p,manifest)


if __name__=="__main__":
    unittest.main()
