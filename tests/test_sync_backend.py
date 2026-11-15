"""scripts/sync_backend.py never turns newer work in backend/ back into the older original, and the conclusion modules survive it.

Everything runs in temporary folders; the real backend/ and the real original are never read or written, and nothing is
run against production.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import sync_backend as sb  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Folders(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sync-test-"))
        self.original, self.backend = self.tmp / "original", self.tmp / "backend"
        self.original.mkdir()
        self.backend.mkdir()
        (self.original / "webapp.py").write_text("# original webapp v2\n")
        self.runtime = ("webapp.py", "lib/")
        self.local = ("mine.py",)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def put(self, folder: Path, name: str, text: str) -> Path:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_sync(self, **kw):
        return sb.sync(self.original, self.backend, self.runtime, self.local, **kw)

    def manifest(self):
        return json.loads((self.backend / "BACKEND_FILES.json").read_text())


class Rules(Folders):
    def setUp(self):
        super().setUp()
        self.put(self.backend, "mine.py", "# only here\n")

    def test_a_new_file_is_copied_and_recorded(self):
        self.put(self.original, "lib/a.py", "a1\n")
        result = self.run_sync()
        self.assertIn("lib/a.py", result["plan"]["new"])
        self.assertEqual((self.backend / "lib" / "a.py").read_text(), "a1\n")
        self.assertEqual(self.manifest()["files"]["lib/a.py"], sha(self.backend / "lib" / "a.py"))

    def test_a_file_never_edited_here_is_updated_from_a_newer_original(self):
        self.put(self.original, "lib/a.py", "a1\n")
        self.run_sync()
        self.put(self.original, "lib/a.py", "a2 newer\n")
        result = self.run_sync()
        self.assertIn("lib/a.py", result["plan"]["updated"])
        self.assertEqual((self.backend / "lib" / "a.py").read_text(), "a2 newer\n")

    def test_a_file_edited_here_is_not_overwritten_by_the_older_original(self):
        self.put(self.original, "lib/a.py", "a1\n")
        self.run_sync()
        synced_hash = self.manifest()["files"]["lib/a.py"]
        mine = self.put(self.backend, "lib/a.py", "a1 + my newer work\n")
        self.put(self.original, "lib/a.py", "a2\n")
        before = mine.read_bytes()
        result = self.run_sync()
        self.assertEqual(result["conflicts"], ["lib/a.py"])
        self.assertEqual(mine.read_bytes(), before, "the newer file was left exactly as it was")
        self.assertEqual(self.manifest()["files"]["lib/a.py"], synced_hash, "it stays visible as edited")

    def test_a_conflict_is_reported_again_on_the_next_run(self):
        self.put(self.original, "lib/a.py", "a1\n")
        self.run_sync()
        self.put(self.backend, "lib/a.py", "edited\n")
        self.put(self.original, "lib/a.py", "a2\n")
        self.assertEqual(self.run_sync()["conflicts"], ["lib/a.py"])
        self.assertEqual(self.run_sync()["conflicts"], ["lib/a.py"])

    def test_force_overwrites_a_conflict_but_never_a_local_module(self):
        self.put(self.original, "lib/a.py", "a1\n")
        self.run_sync()
        self.put(self.backend, "lib/a.py", "edited\n")
        self.put(self.original, "lib/a.py", "a2\n")
        self.put(self.original, "mine.py", "# an older mine in the original\n")
        result = self.run_sync(force=True)
        self.assertEqual((self.backend / "lib" / "a.py").read_text(), "a2\n")
        self.assertEqual(result["conflicts"], [])
        self.assertEqual((self.backend / "mine.py").read_text(), "# only here\n")

    def test_local_files_are_never_deleted_or_listed_as_copied(self):
        self.put(self.backend, "lib/extra_local.py", "x\n")  # in a copied folder, but not in the original
        self.put(self.original, "lib/a.py", "a1\n")
        self.run_sync()
        self.run_sync()
        self.assertTrue((self.backend / "lib" / "extra_local.py").is_file())
        self.assertTrue((self.backend / "mine.py").is_file())
        self.assertNotIn("mine.py", self.manifest()["files"])
        self.assertIn("mine.py", self.manifest()["local_modules"])

    def test_a_file_gone_from_the_original_is_removed_only_if_never_edited_here(self):
        for name in ("lib/keep.py", "lib/drop.py"):
            self.put(self.original, name, f"{name}\n")
        self.run_sync()
        self.put(self.backend, "lib/keep.py", "edited here\n")
        (self.original / "lib" / "keep.py").unlink()
        (self.original / "lib" / "drop.py").unlink()
        self.put(self.original, "lib/other.py", "o\n")
        result = self.run_sync()
        self.assertEqual(result["plan"]["removed"], ["lib/drop.py"])
        self.assertEqual(result["plan"]["kept"], ["lib/keep.py"])
        self.assertFalse((self.backend / "lib" / "drop.py").exists())
        self.assertEqual((self.backend / "lib" / "keep.py").read_text(), "edited here\n")

    def test_dry_run_writes_nothing(self):
        self.put(self.original, "lib/a.py", "a1\n")
        self.run_sync()
        self.put(self.original, "lib/a.py", "a2\n")
        self.put(self.original, "lib/b.py", "b\n")
        manifest = (self.backend / "BACKEND_FILES.json").read_bytes()
        result = self.run_sync(dry_run=True)
        self.assertEqual(result["plan"]["new"], ["lib/b.py"])
        self.assertEqual(result["plan"]["updated"], ["lib/a.py"])
        self.assertFalse((self.backend / "lib" / "b.py").exists())
        self.assertEqual((self.backend / "lib" / "a.py").read_text(), "a1\n")
        self.assertEqual((self.backend / "BACKEND_FILES.json").read_bytes(), manifest)

    def test_a_missing_local_module_stops_the_sync_loudly(self):
        self.put(self.original, "lib/a.py", "a1\n")
        (self.backend / "mine.py").unlink()
        with self.assertRaises(SystemExit) as raised:
            self.run_sync()
        self.assertIn("mine.py", str(raised.exception))

    def test_a_file_never_recorded_but_different_is_a_conflict_not_a_replacement(self):
        self.put(self.original, "lib/a.py", "a1\n")
        self.put(self.backend, "webapp.py", "# newer webapp from here, never synced\n")
        result = self.run_sync()
        self.assertEqual(result["conflicts"], ["webapp.py"])
        self.assertEqual((self.backend / "webapp.py").read_text(), "# newer webapp from here, never synced\n")


class TheRealFeatureSurvives(unittest.TestCase):
    """Old production files as the 'original'; the real backend as the working copy that carries the feature."""

    def test_the_conclusion_generator_survives_a_sync_against_older_originals(self):
        old = {}
        for name in ("webapp.py", "dashboard_utils.py"):
            shown = subprocess.run(["git", "show", f"deployment:backend/{name}"], cwd=ROOT, capture_output=True)
            if shown.returncode != 0:
                self.skipTest("the deployment branch is not available here")
            old[name] = shown.stdout
        tmp = Path(tempfile.mkdtemp(prefix="sync-real-"))
        try:
            original, backend = tmp / "original", tmp / "backend"
            original.mkdir()
            backend.mkdir()
            for name, data in old.items():
                (original / name).write_bytes(data)
            for name in ("webapp.py", "dashboard_utils.py") + sb.LOCAL_MODULES:
                shutil.copyfile(ROOT / "backend" / name, backend / name)
            shutil.copytree(ROOT / "backend" / "sentiment-analysis" / "defaketive_sentiment", backend / "sentiment-analysis" / "defaketive_sentiment", ignore=shutil.ignore_patterns("__pycache__"))
            # as if the last sync had written the OLD versions and the files were edited here afterwards
            (backend / "BACKEND_FILES.json").write_text(json.dumps({"files": {name: hashlib.sha256(data).hexdigest() for name, data in old.items()}}))
            mine_before = {name: sha(backend / name) for name in ("webapp.py", "dashboard_utils.py", "aspects.py")}

            result = sb.sync(original, backend, ("webapp.py", "dashboard_utils.py"), sb.LOCAL_MODULES)

            self.assertEqual(sorted(result["conflicts"]), ["dashboard_utils.py", "webapp.py"])
            self.assertEqual({name: sha(backend / name) for name in mine_before}, mine_before, "nothing was overwritten")
            for name in sb.LOCAL_MODULES:
                self.assertTrue((backend / name).is_file(), name)
            # and the feature still works from the synced folder
            script = (
                "import gzip, json, sys\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "import dashboard_utils as du\n"
                "products = [x['product'] for x in json.load(gzip.open(sys.argv[2], 'rt', encoding='utf-8'))]\n"
                "c = du.badge_view(products[0], aspects=True)['conclusion']\n"
                "print(json.dumps({'why': len(c['evidence']['why']), 'decision': c['decision'], 'file': du.__file__}))\n"
            )
            ran = subprocess.run([sys.executable, "-I", "-c", script, str(backend), str(ROOT / "backend" / "seed" / "saved_products.json.gz")], capture_output=True, text=True, cwd=tmp)
            self.assertEqual(ran.returncode, 0, ran.stderr[-800:])
            out = json.loads(ran.stdout)
            self.assertGreater(out["why"], 0)
            self.assertTrue(out["file"].startswith(str(backend)), "it ran from the synced folder, not the project")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_blind_copy_would_have_lost_the_feature(self):
        """The reason the guard exists: the older original has no conclusion modules and no aspects argument."""
        shown = subprocess.run(["git", "show", "deployment:backend/dashboard_utils.py"], cwd=ROOT, capture_output=True)
        if shown.returncode != 0:
            self.skipTest("the deployment branch is not available here")
        self.assertNotIn(b"aspect_evidence", shown.stdout)
        self.assertIn(b"aspect_evidence", (ROOT / "backend" / "dashboard_utils.py").read_bytes())


class RealRepository(unittest.TestCase):
    def test_every_local_module_exists_and_is_never_a_copied_file(self):
        manifest = json.loads((ROOT / "backend" / "BACKEND_FILES.json").read_text())
        for name in sb.LOCAL_MODULES:
            self.assertTrue((ROOT / "backend" / name).is_file(), name)
            self.assertNotIn(name, manifest["files"], "a local module must not be listed as copied from the original")
            self.assertFalse(any(entry == name or (entry.endswith("/") and name.startswith(entry)) for entry in sb.RUNTIME), "and must not be in the copy list")

    def test_every_backend_module_the_conclusion_imports_is_accounted_for(self):
        """A new module imported by the conclusion code but neither copied nor local would be lost silently."""
        copied = set(json.loads((ROOT / "backend" / "BACKEND_FILES.json").read_text())["files"]) | set(sb.LOCAL_MODULES)
        for name in ("dashboard_utils.py", "aspects.py", "conclusion_text.py", "aspect_profiles.py"):
            text = (ROOT / "backend" / name).read_text(encoding="utf-8")
            for module in ("category_copy", "aspect_profiles", "aspects", "conclusion_text"):
                if f"import {module}" in text or f"from {module} import" in text:
                    self.assertIn(f"{module}.py", copied, f"{name} imports {module}, which the sync does not know")


if __name__ == "__main__":
    unittest.main()
