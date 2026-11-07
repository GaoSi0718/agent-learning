"""Runner regression tests; all subprocess fixtures are synthetic and offline."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RUNNER = Path(__file__).resolve().parents[1] / "tools" / "run_all_tests.py"
spec = importlib.util.spec_from_file_location("runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tests = self.root / "w6_hr_policy" / "tests"
        self.tests.mkdir(parents=True)
        (self.root / "tools").mkdir()
        (self.root / "tools" / "run_all_tests.py").write_bytes(RUNNER.read_bytes())

    def script(self, name, body):
        path = self.tests / name
        path.write_text(body, encoding="utf-8")
        return path

    def run_gate(self, *args):
        return subprocess.run([sys.executable, str(self.root / "tools" / "run_all_tests.py"), *args],
                              capture_output=True, text=True, encoding="utf-8")

    def test_default_never_executes_judge(self):
        self.script("test_b1_context_compact.py", "print('ok')")
        self.script("test_eval_gate.py", "raise AssertionError('API test was executed')")
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS 1 / FAIL 0 / SKIP 1", result.stdout)
        self.assertNotIn("API test was executed", result.stdout)

    def test_selected_legacy_skip_is_not_pass(self):
        self.script("test_b1_context_compact.py", "print('ok')")
        self.script("test_eval_gate.py", "print('SKIP: key missing')")
        result = self.run_gate("--e2e")
        self.assertEqual(result.returncode, 77)
        self.assertIn("PASS 1 / FAIL 0 / SKIP 1", result.stdout)

    def test_explicit_skip_exit_code(self):
        self.script("test_b1_context_compact.py", "raise SystemExit(77)")
        result = self.run_gate()
        self.assertEqual(result.returncode, 77)
        self.assertIn("PASS 0 / FAIL 0 / SKIP 1", result.stdout)

    def test_unknown_test_is_not_executed(self):
        self.script("test_new_api.py", "raise AssertionError('must not run')")
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("unclassified", result.stdout)
        self.assertNotIn("must not run", result.stdout)

    def test_failure_keeps_stderr_and_overrides_skip(self):
        self.script("test_b1_context_compact.py", "print('SKIP: earlier check'); raise ValueError('failure detail')")
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("ValueError: failure detail", result.stdout)
        self.assertIn("PASS 0 / FAIL 1 / SKIP 0", result.stdout)

    def test_empty_suite_is_not_success(self):
        self.assertEqual(self.run_gate().returncode, 1)

    def test_timeout_is_failure(self):
        path = self.script("test_b1_context_compact.py", "import time; time.sleep(10)")
        with patch.object(runner, "ROOT", self.root), patch.object(runner, "PER_TEST_TIMEOUT", 0.1):
            mark, _, output = runner.run_one(sys.executable, path)
        self.assertEqual(mark, "FAIL")
        self.assertIn("Timeout", output)


if __name__ == "__main__":
    unittest.main()
