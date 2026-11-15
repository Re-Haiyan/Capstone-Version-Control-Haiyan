"""Regression tests for benchmark integrity; do not run the heavy measurement."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "research" / "product_specific_conclusions" / "benchmark.py"
spec = importlib.util.spec_from_file_location("conclusion_benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class BenchmarkIntegrityTests(unittest.TestCase):
    def test_linux_restricted_cpu_ids_are_respected(self):
        """A cgroup may expose CPUs {24, 26, 28}, not CPU 0 and CPU 1."""
        with (
            mock.patch.object(benchmark.os, "sched_getaffinity",
                              side_effect=[{24, 26, 28}, {24, 26}], create=True),
            mock.patch.object(benchmark.os, "sched_setaffinity", create=True) as set_affinity,
        ):
            self.assertEqual(benchmark.limit_cpus(2), 2)
            set_affinity.assert_called_once_with(0, {24, 26})

    def test_refuses_to_request_more_cpus_than_allowed(self):
        with (
            mock.patch.object(benchmark.os, "sched_getaffinity",
                              return_value={32, 34}, create=True),
            mock.patch.object(benchmark.os, "sched_setaffinity", create=True) as set_affinity,
        ):
            with self.assertRaises(ValueError):
                benchmark.limit_cpus(4)
            set_affinity.assert_not_called()

    def test_rejects_zero_or_negative_affinity(self):
        for value in (0, -1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    benchmark.limit_cpus(value)

    def test_rejects_unsafe_tag_before_running_benchmark(self):
        run = subprocess.run(
            [sys.executable, str(SCRIPT), "--tag", "../outside"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 2)
        self.assertIn("--tag must be", run.stderr)


if __name__ == "__main__":
    unittest.main()
